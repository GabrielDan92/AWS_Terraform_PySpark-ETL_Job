variable "iam_role" {
  type    = string
  default = ""
}

variable "s3_name" {
  type    = string
  default = "spark-etl-glue-job22"
}

variable "glue_name" {
  type    = string
  default = "sparkTC22"
}

variable "glue_db_name" {
  type    = string
  default = "glue-sparktc-db22"
}

variable "glue_job_name" {
  type    = string
  default = "glueJob"
}
