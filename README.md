## Objective:
The project's objective is to use Terraform's IaC (Infrastructure as Code) solution for creating several AWS services for an ETL job. The ETL job reads two different input JSON files from an S3 bucket, processes them through PySpark in a Glue Job, then outputs a third JSON file in S3 as result.
<br /><br />
 
 ## Prerequisites:
 To succesfully run the Terraform configuration and create the AWS resources you will need:
  - The Terraform CLI installed - install instructions [here](https://learn.hashicorp.com/tutorials/terraform/install-cli?in=terraform/aws-get-started)
  - The AWS CLI installed - install instructions [here](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
  - An AWS account
  - Your AWS credentials (AWS Access Key ID & AWS Secret Access Key) + being successfully authenticated in AWS CLI, using ```aws configure```
  - An IAM role with the ```AWSGlueServiceRole``` policy plus an inline policy for read/write access to S3
  - The IAM role ARN must be saved in the ```variables.tf``` file, variable ```iam_role```
  - Using the terminal, ```cd``` in the folder where you saved the repo files (```stations.json```, ```trips.json```, ```glu-spark-job.py```, ```main.tf```, ```variables.tf```)
<br />
  
## To start the Terraform configuration run the following commands:
  - ```terraform init```
  - ```terraform fmt``` (optional - used for formatting the configuration file)
  - ```terraform validate``` (optional - used for validating the configuration fie)
  - ```terraform apply```
  - ```terraform destroy``` (optional - used for deleting the AWS resources after using them)  
<br />
 
## The following steps are applied automatically by Terraform:
  * Create an S3 bucket
  * Create S3 ```input```, ```output```, ```script```, ```logs``` and ```temp``` folders - ***I know that Amazon S3 has a flat structure instead of a hierarchy like you would see in a file system, but for the sake of organizational simplicity, the Amazon S3 console supports the folder concept as a means of grouping objects***
  * Upload the ```JSON``` input files and the ```.py``` Pyspark script in their corresponding S3 folders
  * Create the AWS Glue Crawler, referencing the input files
  * Start the Glue Crawler
  * Wait until the Crawler creates the metadata Glue Data Catalog
  * Create the Glue Job, referencing the Data Catalog created by the Glue Crawler and the ```.py``` PySpark script from S3
  * Run the Glue Job and save the output back to the S3 bucket
<br />
 
## The Glue Job:
The entire logic of the Glue Job is based on the ```.py``` PySpark script. Using PySpark, I'm reading the following ```JSON``` data sets from the S3 bucket:
##### Data Set 1 - stations:
```javascript
{
    "stations": {
        "internal_bus_station_id": [
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9
        ], 
        "public_bus_station": [
            "BAutogara", "BVAutogara", "SBAutogara", "CJAutogara", "MMAutogara","ISAutogara", "CTAutogara", "TMAutogara", "BCAutogara", "MSAutogara"
        ]
    }
}
```
##### Data Set 2 - trips:
```javascript
{
    "trips": {
            "origin": [
                "B","B","BV","TM","CJ"
            ],
            "destination": [
                "SB","MM", "IS","CT","SB"
            ],
            "internal_bus_station_ids": [
                [0,2],[0,2,4],[1,8,3,5],[7,2,9,4,6],[3,9,5,6,7,8]
            ],
            "triptimes": [
                ["2021-03-01 06:00:00", "2021-03-01 09:10:00"],
                ["2021-03-01 10:10:00", "2021-03-01 12:20:10", "2021-03-01 14:10:10"],
                ["2021-04-01 08:10:00", "2021-04-01 12:20:10", "2021-04-01 15:10:00", "2021-04-01 15:45:00"],
                ["2021-05-01 10:45:00", "2021-05-01 12:20:10", "2021-05-01 18:30:00", "2021-05-01 20:45:00", "2021-05-01 22:00:00"],
                ["2021-05-01 07:10:00", "2021-05-01 10:20:00", "2021-05-01 12:30:00", "2021-05-01 13:25:00", "2021-05-01 14:35:00", "2021-05-01 15:45:00"]
            ]
        }
}
```
And after calculating the trip times of each trip in column ```duration_min``` and replacing the ```bus_stations_ids``` column with stations' names, I'm outputing the following ```JSON``` file in S3 as response:

##### PySpark JSON result:
```javascript
{
    "result": [
        {
            "row_num": 1,
            "origin": "B",
            "destination": "SB",
            "pubic_bus_stops": [
                "BAutogara",
                "SBAutogara"
            ],
            "duration_min": "190.0 min"
        },
        {
            "row_num": 2,
            "origin": "B",
            "destination": "MM",
            "pubic_bus_stops": [
                "BAutogara",
                "SBAutogara",
                "MMAutogara"
            ],
            "duration_min": "240.0 min"
        },
        {
            "row_num": 3,
            "origin": "BV",
            "destination": "IS",
            "pubic_bus_stops": [
                "BVAutogara",
                "BCAutogara",
                "CJAutogara",
                "ISAutogara"
            ],
            "duration_min": "455.0 min"
        },
        {
            "row_num": 4,
            "origin": "CJ",
            "destination": "SB",
            "pubic_bus_stops": [
                "CJAutogara",
                "MSAutogara",
                "ISAutogara",
                "CTAutogara",
                "TMAutogara",
                "BCAutogara",
                "SBAutogara"
            ],
            "duration_min": "730.0 min"
        },
        {
            "row_num": 5,
            "origin": "TM",
            "destination": "CT",
            "pubic_bus_stops": [
                "TMAutogara",
                "SBAutogara",
                "MSAutogara",
                "MMAutogara",
                "CTAutogara"
            ],
            "duration_min": "675.0 min"
        }
    ]
}
```
