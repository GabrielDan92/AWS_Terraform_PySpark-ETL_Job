terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

provider "aws" {
  region = "eu-central-1"
}

#######################
# S3 + folders + files
#######################

# create the S3 bucket
resource "aws_s3_bucket" "b" {
  bucket = var.s3_name
}

# create the S3 folders
resource "aws_s3_bucket_object" "input" {
  bucket = aws_s3_bucket.b.id
  key    = "input/"
}
resource "aws_s3_bucket_object" "output" {
  bucket = aws_s3_bucket.b.id
  key    = "output/"
}
resource "aws_s3_bucket_object" "scripts" {
  bucket = aws_s3_bucket.b.id
  key    = "scripts/"
}
resource "aws_s3_bucket_object" "logs" {
  bucket = aws_s3_bucket.b.id
  key    = "logs/"
}
resource "aws_s3_bucket_object" "temp" {
  bucket = aws_s3_bucket.b.id
  key    = "temp/"
}

# upload the JSON input files and the .py script to S3
resource "aws_s3_bucket_object" "stations" {
  bucket = aws_s3_bucket.b.id
  key    = "${aws_s3_bucket_object.input.id}/stations.json"
  source = "stations.json"
}
resource "aws_s3_bucket_object" "trips" {
  bucket = aws_s3_bucket.b.id
  key    = "${aws_s3_bucket_object.input.id}/trips.json"
  source = "trips.json"
}
resource "aws_s3_bucket_object" "glueScript" {
  bucket = aws_s3_bucket.b.id
  key    = "${aws_s3_bucket_object.scripts.id}/glue-spark-job.py"
  source = "glue-spark-job.py"
}

#######################
# Glue Crawler
#######################
resource "aws_glue_crawler" "crawler" {
  database_name = var.glue_db_name
  name          = var.glue_name
  role          = var.iam_role

  s3_target {
    path = "${aws_s3_bucket.b.id}/input"
  }

  # run the crawler after creating it
  provisioner "local-exec" {
    command = "aws glue start-crawler --name ${self.name}"
  }
}

#######################
# Glue Job
#######################

# wait 50 seconds before creating the Glue Job
resource "time_sleep" "wait_for_crawler" {
  create_duration = "50s"
  depends_on      = [aws_glue_crawler.crawler]
}

resource "aws_glue_job" "glueJob" {
  depends_on = [time_sleep.wait_for_crawler]

  name              = var.glue_job_name
  role_arn          = var.iam_role
  max_retries       = 0
  timeout           = 10
  glue_version      = "3.0"
  worker_type       = "G.1X"
  number_of_workers = 2

  command {
    script_location = "s3://${aws_s3_bucket.b.id}/scripts/glue-spark-job.py"
    python_version  = "3"
  }

  # run the job after creating it
  provisioner "local-exec" {
    command = "aws glue start-job-run --job-name ${self.name}"
  }

  default_arguments = {
    "--job-language"                     = "python"
    "--spark-event-logs-path"            = "s3://${aws_s3_bucket.b.id}/logs/"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-continuous-log-filter"     = "true"
    "--enable-spark-ui"                  = "true"
    "--job-bookmark-option"              = "job-bookmark-enable"
    "--TempDir"                          = "s3://${aws_s3_bucket.b.id}/temp/"
  }
}
