import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql import SparkSession
from pyspark.sql.window import Window
from pyspark.sql.types import StringType
from pyspark.sql.functions import arrays_zip, row_number, lit, col, concat, element_at, explode, to_timestamp, struct, collect_list, round

# initialize the PySpark session
spark_context = SparkContext.getOrCreate()
glue_context = GlueContext(spark_context)
session = glue_context.spark_session

# parameters
glue_db = "glue-sparktc-db22"
glue_tbl1 = "trips_json"
glue_tbl2 = "stations_json"
s3_write_path = "s3://spark-etl-glue-job22/output/"

# read the json files from the Glue catalog
stations = glue_context.create_dynamic_frame.from_catalog(database = glue_db, table_name = glue_tbl2)
trips = glue_context.create_dynamic_frame.from_catalog(database = glue_db, table_name = glue_tbl1)
stationsDF = stations.toDF()
tripsDF = trips.toDF()
stationsDF = stationsDF.select("stations.*")
tripsDF = tripsDF.select("trips.*")

# explode the JSON arrays and add each array element in its own row
tripsDF = tripsDF.withColumn("new", arrays_zip("origin", "destination", "internal_bus_station_ids", "triptimes")).withColumn("new", explode("new"))\
            .select(col("new.origin"), col("new.destination"), col("new.internal_bus_station_ids").alias("internal_bus_stations_ids"), col("new.triptimes"))\
            .withColumn("row_num", row_number().over(Window().orderBy("triptimes")))\
            .select("row_num", "origin", "destination", "internal_bus_stations_ids", "triptimes")

stationsDF = stationsDF.withColumn("new", arrays_zip("internal_bus_station_id", "public_bus_station")).withColumn("new", explode("new"))\
            .select(col("new.internal_bus_station_id"), col("new.public_bus_station"))\
            .withColumn("row_num", row_number().over(Window().orderBy("internal_bus_station_id")))\
            .select("row_num", "internal_bus_station_id", "public_bus_station")

# explode internal_bus_stations_ids into individual rows for getting the public name
explodedDF = tripsDF.select("internal_bus_stations_ids", explode("internal_bus_stations_ids")\
            .alias("id")).withColumn("row_num", row_number().over(Window().orderBy("internal_bus_stations_ids")))

# join the individual id rows with the public name from stations table
explodedDF = explodedDF.join(stationsDF, explodedDF.id == stationsDF.internal_bus_station_id)\
            .select(explodedDF["*"], stationsDF["public_bus_station"]).orderBy("row_num")

# group the data by the internal stations ids arrays, generate a struct data type column as result
explodedDF = explodedDF.groupBy("internal_bus_stations_ids").agg(collect_list(struct("public_bus_station")).alias("data"))

# join the found public names back with the internal station ids arrays
tripsDF = tripsDF.join(explodedDF, "internal_bus_stations_ids")\
        .select(tripsDF["*"], explodedDF["data.public_bus_station"].alias("pubic_bus_stops"))

# calculate the duration from origin to destination
tripsDF = tripsDF.withColumn("duration_min", lit(to_timestamp(element_at(tripsDF.triptimes, -1)).cast("long") - to_timestamp(tripsDF.triptimes[0]).cast("long")))
tripsDF = tripsDF.withColumn("duration_min", concat(round(col("duration_min")/60, 0).cast(StringType()), lit(" min")))
tripsDF = tripsDF.orderBy(["row_num"])
tripsDF = tripsDF.select(
    struct(
        col("row_num"),
        col("origin"),
        col("destination"),
        col("pubic_bus_stops"),
        col("duration_min"),
    ).alias("result")
).agg(
    collect_list("result").alias("result"))
tripsDF = tripsDF.repartition(1)

# convert to DynamicFrame
output = DynamicFrame.fromDF(tripsDF, glue_context, "output")

# save the final table in S3
glue_context.write_dynamic_frame.from_options(
    frame = output,
    connection_type = "s3",
    connection_options = {
        "path": s3_write_path,
    },
    format = "json"
)
