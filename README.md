# Forex Forest MT5 Data Fetching Documentation (v0.1)

Table of Contents

1. [Introduction](#1-introduction)
2. [Code Structure and Architecture](#2-code-structure-and-architecture)
3. [Function Descriptions](#3-function-descriptions)
4. [Data Models and Database Schema](#4-data-models-and-database-schema)
5. [Configuration](#5-configuration)
6. [Development Environment](#6-development-environment)
7. [Use Cases](#7-use-cases)

## 1. Introduction

Forex Forest MT5 Data Fetching Script is designed to automate the data fetching process from MT5 to S3. The script can be run in two modes: schedule mode and specific datetime mode. In schedule mode, the script will fetch the data every 4 hours. In specific datetime mode, the script will fetch the data in a specific datetime range.

## 2. Code Structure and Architecture

0. load config yaml
1. initialize mt5
2. fetch 1 tick of data for now
3. data cleaning
4. output dict to csv(need to restructure the data)
5. upload data to "s3://sagemaker-ff-data-bucket/datalake_dev/MT5/{filsename}", and upload log

### MT5 data

|       datetime      |   open  |   high  |   low   |  close  | tick_volume | spread | real_volume |
|:-------------------:|:-------:|:-------:|:-------:|:-------:|:-----------:|:------:|:-----------:|
| 2024-01-14-00-00-00 | 0.89487 | 0.89706 | 0.89034 | 0.89101 |    65339    |    0   |      0      |

### Local data path
{pair}/{pair}_{timeframe}_{datetime}.csv

### S3 data path
{bucket}/datalake_dev/mt5_data/{pair}/{timeframe}/{year}/{month}/{day}/{hour}/{pair}_{timeframe}_{datetime}.csv


## 3. Function Descriptions

### Utils

#### create_local_logger

Create a log and rename it based on the current HK time.

> parameters:

- `local_log_path` (path): Path to the local log
- `logger_name` (str): the format of the logger name should be f"{job_name}\_{hk_datetime_now}

> return:

- None

---

### Data Fetching

#### get_mt5_now_datetime

Get current mt5 datetime, the format will be %Y-%m-%d-%H-00-00.

> parameters:

- None

> return:

- `mt5_now_datetime` (datetime)

  pass to data_fetching function to fetch the current mt5 data

---

TODO: The name of the function is not clear, need to change it

#### change_str_to_target_timezone_datetime

Convert the datetime type from a string to a datetime object with the desired timezone. Typically, the datetime source is obtained from a configuration file.

> parameters:

- `target_datetime` (str): target datetime

- `timezone`: desired timezone

> return:

- `target_datetime` (datetime)

---

#### config_datetime

Based on the job type specified in the configuration file, configure the datetime accordingly. If the job type is set to "now", return the current MT5 datetime obtained from the get_mt5_now_datetime function. If the job type is set to "specific_datetime", return the specific datetime defined in the configuration file. If the job type is set to "range", return the start_datetime and end_datetime values defined in the configuration file.

> parameters:

- `config` : config yaml file

TODO: The return type is not union, need to change it

> return Union[mt5_now_datetime, specific_datetime, start_datetime and end_datetime]:

- `mt5_now_datetime` (datetime)

- `specific_datetime` (datetime)

- `start_datetime` (datetime)

- `end_datetime` (datetime)

---

#### create_local_logger

Generate a local logger with a name that depends on the job name and the current datetime in Hong Kong. Once create logger, the log folder name will be `{name}_logs` logger name will be in the format `{name}_{datetime_now}`.

> parameters:

- `local_log_path` (str): local log path

- `name` (str): job name

> return

- None

---

#### initialize_mt5

Initialize MT5. Return result Ok if MT5 initialized successfully. If initialization fails, try starting MT5 executable file. If initialization still fails, raise an exception and return the result Err

> parameters:

- `mt5_file_path` (Path): Path to the MT5 executable file

> return:

- Union[Ok, Err]

  - Ok: "MT5 initialized successfully"

  - Err: "MT5 initialization failed"

---

#### fetch_specific_datetime_data

Fetch specific datetime data from MetaTrader 5. If retrieve data successfully, return result OK with the value rates. If retrieve empty data, retry the the copy_rates_from function until the retrieved data is not none and return result OK with the value rates. If the number of retry hit the maximum i.e. 5, finish the loop and return result Err.

> parameters:

- symbol (str): The currency pair symbol name

- timeframe (int): timeframe

- specific_datetime (datetime): target datetime

> return :

- Union[Ok, Err]

  - Ok: rates (numpy.ndarray)

        Returns the bars as the numpy array with the named time, open, high, low, close, tick_volume, spread and real_volume columns.

  - Err: "Error in data fetching"

---

#### fetch_range_datetime_data()

Fetch a range of datetime data from MetaTrader 5. If retrieve data successfully, return result OK with the value rates. If retrieve empty data, retry the the copy_rates_from function until the retrieved data is not none and return result OK with the value rates. If the number of retry hit the maximum i.e. 5, finish the loop and return result Err.

> parameters:

- symbol (str): The currency pair symbol name

- timeframe (int): timeframe

- start_datetime (datetime): datetime the bars are requested from

- end_datetime (datetime): datetime, up to which the bars are requested

> return:

- Union[Ok, Err]

  - `Ok`: rates (numpy.ndarray)

        Returns the bars as the numpy array with the named time, open, high, low, close, tick_volume, spread and real_volume columns.

  - `Err`: "Error in data fetching"

---

#### convert_time_to_datetime

Convert time to datetime in DataFrame.

> parameters:

- `data` (pd.DataFrame): the DataFrame with the named time, open, high, low, close, tick_volume, spread and real_volume columns

> return: Union[Ok, Err]

- `Ok` (df (pd.DataFrame))

  A DataFrame with the named datetime, open, high, low, close and tick volume, spread and real_volume columns.

- `Err`("The DataFrame is none")

  If the df is empty, return Err

---

#### output_df_to_csv

Output DataFrame to a csv file.

> parameters:

- `df` (pd.DataFrame): DataFrame

- `pair` (str): The currency pair name

- `timeframe` (str): The timeframe of the data

- `datetime_str` (str): datetime string

- `local_data_base_path` (Path): The local data base path

> return: Union[Ok, Err]

- `Ok`(output_file)

  The output file is the file output path

- `Err`(f"{output_file} does not exist")

---

#### split_df_into_rows

Takes a DataFrame df as input and splits it into multiple smaller DataFrames, each containing a single row from the original DataFrame.

> parameters:

- `df` (pd.DataFrame): DataFrame

> return:

- `dfs` (list)

  a list of pandas DataFrames

#### fetch_output_range_data_to_csv

Retrieve a range of datetime data, convert time to the datetime, and export it to a CSV file.

> parameters:

- `local_data_base_path` (Path): teh local data base path

- start_datetime (datetime): start datetime

- end_datetime (datetime): end datetime

- timeframes (dict): timeframes

> return: Union[Ok, Err]

- Ok("Finish fetching and output range of data to csv")

- Err(f"Error in fetching and output range of data to csv: {e}")

---

#### fetch_output_data_to_csv

Retrieve a specific datetime data, convert time to the datetime, and export it to a CSV file.

> parameters:

- `local_data_base_path` (Path): teh local data base path

- start_datetime (datetime): start datetime

- end_datetime (datetime): end datetime

- timeframes (dict): timeframes

> return: Union[Ok, Err]

- Ok("Finish fetching and output range of data to csv")

- Err(f"Error in fetching and output range of data to csv: {e}")

---

#### upload_data_to_s3

Upload local data folder to S3.

> parameters:

- local_data_base_path (Path): local data source path

- s3_output_base_path (S3Path): S3 destination path

> return: Union[Ok, Err]

- Ok("Finish uploading")

- Err(f"Error uploading {local_file_path} to {s3_pair_path}: {e}")

  local file path is the path for each pair, s3 pair path is the path for each pair

---

#### upload_latest_log_to_s3

Get the latest log file and upload to S3, avoid upload irrelevant log files.

> parameters:

- local_log_path (Str): local data source path

- s3_output_base_path (S3Path): S3 destination path

> return: Union[Ok, Err]

- Ok(f"{latest_log_file} uploaded to {s3_output_base_path}")

- Err(f"Error uploading {latest_log_file} to {s3_output_base_path}: {e}")

---

#### delete_local_data

Delete local data folder.

> parameters:

- local_data_base_path (Path): local data source path

> return:

- None

---

#### delete_all_local_data

Delete local data and log.

TODO: duplicate argument name

> parameters:

- local_data_base_path (Path): local data source path

- local_data_base_path (Path): local data source path

> return:

- None

---

#### data_fetching_job

Depending on the job attribute specified in the input configuration file, retrieve the data, convert the time to the datetime, and export it to a CSV file.

> parameters:

- config_file_name_str (str): config file name

> return: Union[Ok, Err]

- Ok(f"Finish data fetching job")

- Err

  If one of the data fetching step return Err, then return Err

---

### Database.py

#### get_database_credentials(secret_name, profile_name)

Retrieve database credentials securely using AWS Secrets Manager.

> parameters:

- `secret_name` (str): The name of the secret in AWS Secrets Manager.
- `profile_name` (str): The AWS profile name to use for accessing AWS services.

> return:

- Union[Ok, Err]

  - Ok: A dictionary containing the database credentials if the retrieval is successful.
  - Err: An error message string if the retrieval fails.

---

#### get_database_engine(secret_name, profile_name, database_name)

Create and return a database engine connection using credentials from AWS Secrets Manager.

> parameters:

- `secret_name` (str, default="RDS_database"): The name of the secret containing database credentials in AWS Secrets Manager.
- `profile_name` (str, default="data-storage-administrator-440197809615"): The AWS profile name for accessing AWS services.
- `database_name` (str, default="MT5_test_data"): The name of the database to connect to.

> return:

- Union[Ok, Err]

  - Ok: A SQLAlchemy engine object if the connection is successful.
  - Err: An error message string if the connection fails.

---

### Database

## 4. Data Models and Database Schema

### Data Models

TODO: Fill in the data models

#### MT5 Data

|       datetime      |   open  |   high  |   low   |  close  | tick_volume | spread | real_volume |
|:-------------------:|:-------:|:-------:|:-------:|:-------:|:-----------:|:------:|:-----------:|
| 2024-01-14-00-00-00 | 0.89487 | 0.89706 | 0.89034 | 0.89101 |    65339    |    0   |      0      |

### Database Schema

## 5. Configuration

### schedule_data_fetching_config.yaml

- type: "now"

- aws: bucket_name

- data_fetching:

  - s3_data_output_base_path

### on_demand_data_fetching_config.yaml

- type: "specific_datetime"
  specific_datetime:
  start_datetime:
  end_datetime:

> remark: it can be a range or a specific datetime

- aws: bucket_name

- data_fetching:

  - s3_data_output_base_path

## 6. Development Environment

### Python Version

- Python 3.10.0

TODO: Add the python packages

### Python Packages

- boto3
- cloudpathlib
- pandas
- pendulum
- result
- pymysql

### Pre-commit

`pre-commit` detects problems before they enter your version control system, let's you fix them, or fixes them automatically. Here, it will automatically help fixing the problems before commiting

#### Hook

- `trailing-whitespace` : Trims trailing whitespace and enforces a newline at the end of a file.
- `nb-clean` : Cleans Jupyter Notebooks of outputs and metadata.
- `nbqa-black` : Formats Jupyter Notebooks with black.

#### Installation

```bash
pip install pre-commit
```

#### Usage

```bash
pre-commit install
```

#### Remark

- Change the pre-commit `/bin/sh` to `/usr/bin/env sh` in `.git/hooks/pre-commit`. Otherwise, the pre-commit will not work.

#### Add a new hook

- Change the `.pre-commit-config.yaml` file.
- Run `pre-commit install` again.

## 7. Use Cases

### Case 1: schedule data fetching

Open schedule_mt5_data_fetching notebook and run all the cell. The default config yaml file is schedule_config.yaml.

### Case 2: fetch data on demand

Open on_demand_data_fetching notebook and run all the cell. The default config yaml file is on_demand_config.yaml. You can change the type of datetime, if you change it to specific datetime, please remember specify it in the configuration file.
