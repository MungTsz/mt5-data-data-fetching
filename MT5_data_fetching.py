# %%
import os
import yaml
import pytz
import shutil
import pendulum
import datetime
import numpy as np
import pandas as pd
from pathlib import Path
import MetaTrader5 as mt5
from loguru import logger
from cloudpathlib import S3Path
from utils.logger import configure_logger
from result import Err, Ok, is_ok, is_err
from utils.constants import timeframes, PAIRS_WITH_XAU


# %%
def get_mt5_now_datetime():
    mt5_tz = pytz.timezone("Israel")
    mt5_now_datetime = datetime.datetime.now(mt5_tz)
    return mt5_now_datetime


# %%
def change_str_to_target_timezone_datetime(
    target_datetime_str: str, timezone
) -> datetime:
    target_datetime = datetime.datetime.strptime(
        target_datetime_str, "%Y-%m-%d-%H-%M-%S"
    )
    target_datetime = timezone.localize(target_datetime)
    return target_datetime


# %%
def config_datetime(config) -> Ok[str | list] | Err[str]:
    utc_timezone = pytz.timezone("UTC")
    type = config["type"]

    try:
        if type == "now":
            now = get_mt5_now_datetime()
            now_str = now.strftime("%Y-%m-%d-%H-%M-%S")
            mt5_now_datetime = change_str_to_target_timezone_datetime(
                now_str, utc_timezone
            )
            return Ok(mt5_now_datetime)
        elif type == "specific_datetime":
            specific_datetime_str = config["specific_datetime"]
            specific_datetime = change_str_to_target_timezone_datetime(
                specific_datetime_str, utc_timezone
            )
            return Ok(specific_datetime)
        elif type == "range":
            datetime_list = []
            start_datetime_str = config["start_datetime"]
            start_datetime = change_str_to_target_timezone_datetime(
                start_datetime_str, utc_timezone
            )
            datetime_list.append(start_datetime)

            end_datetime_str = config["end_datetime"]
            end_datetime = change_str_to_target_timezone_datetime(
                end_datetime_str, utc_timezone
            )
            datetime_list.append(end_datetime)
            return Ok(datetime_list)
    except Exception as e:
        return Err(f"Error in configuring datetime: {e}")


# %%
def config_timeframe(config):
    timeframe_list = config["timeframe_list"]
    try:
        if timeframe_list[0] == "all":
            timeframe_dict = timeframes
            return Ok(timeframe_dict)
        elif timeframe_list[0] != "all":
            timeframe_dict = {key: timeframes[key] for key in timeframe_list}
            return Ok(timeframe_dict)
    except Exception as e:
        return Err(f"Error in configuring timeframe: {e}")


# %%
def config_pair(config):
    pair_list = config["pair_list"]

    try:
        if pair_list[0] == "all":
            pair_list = PAIRS_WITH_XAU
            return Ok(pair_list)
        elif pair_list[0] != "all":
            # Check if all elements in pair_list are in PAIRS_WITH_XAU list, avoid misspelling
            is_all_in_PAIRS_WITH_XAU = all(item in PAIRS_WITH_XAU for item in pair_list)
            unmatched_items = [item for item in pair_list if item not in PAIRS_WITH_XAU]
            if is_all_in_PAIRS_WITH_XAU is False:
                return Err(
                    f"Error in configuring pair, unmatched items found: {unmatched_items}"
                )
            return Ok(pair_list)
    except Exception as e:
        return Err(f"Error in configuring pair: {e}")


# %%
def create_local_logger(local_log_path_name: str, logger_name: str):
    datetime_now = pendulum.now("Asia/Hong_Kong").strftime("%Y-%m-%d-%H-%M-%S")
    configure_logger(local_log_path_name, f"{logger_name}_{datetime_now}")
    logger.success("Logger configured successfully")


# %%
def initialize_mt5(mt5_file_path: Path):
    if mt5.initialize():
        return Ok("MT5 initialized successfully")

    try:
        logger.info("Finding the MT5 executable file")
        os.startfile(mt5_file_path)
    # if cannot find the file, catch the error msg and return false
    except Exception as e:
        logger.error(f"Error starting MT5: {e}")
        return Err("MT5 initialization failed")

    # if cannot find the file, catch the error msg and return false
    if not mt5.initialize():
        return Err("MT5 initialization failed")


# %%
def fetch_range_datetime_data(
    symbol: str, timeframe: int, start_datetime: datetime, end_datetime: datetime
) -> np.array:
    NUMBER_OF_RETRY = 5

    for i in range(NUMBER_OF_RETRY):
        rates = mt5.copy_rates_range(symbol, timeframe, start_datetime, end_datetime)
        if rates is not None:
            return Ok(rates)
    return Err("Error in data fetching")


# %%
def fetch_specific_datetime_data(
    symbol: str, timeframe: int, specific_datetime: datetime
):
    NUMBER_OF_RETRY = 5

    for i in range(NUMBER_OF_RETRY):
        rates = mt5.copy_rates_from(symbol, timeframe, specific_datetime, 1)
        if rates is not None:
            return Ok(rates)
    return Err("Error in data fetching")


# %%
def convert_time_to_datetime(data: pd.DataFrame):
    df = data.assign(
        time=pd.to_datetime(data["time"], unit="s"),
        Date=lambda x: x["time"].dt.date,
        Time=lambda x: x["time"].dt.time,
    )

    df["datetime"] = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Time"].astype(str)
    )
    df = df.drop(["time", "Date", "Time"], axis=1)

    cols = df.columns.tolist()
    cols.remove("datetime")
    cols.insert(0, "datetime")
    df["datetime"] = df["datetime"].dt.strftime("%Y-%m-%d-%H-%M-%S")
    df = df[cols]
    if df is None:
        return Err("The DataFrame is none")
    return Ok(df)


# %%
def output_df_to_csv(
    df: pd.DataFrame,
    pair: str,
    timeframe: str,
    datetime_str: str,
    local_data_base_path: Path,
):
    output_path = local_data_base_path / pair
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / f"{pair}_{timeframe}_{datetime_str}.csv"
    df.to_csv(output_file, index=False)
    if not output_file.exists():
        return Err(f"{output_file} does not exist")
    return Ok(output_file)


# %%
def split_df_into_rows(df: pd.DataFrame) -> list:
    dfs = []
    row_count = len(df)
    for i in range(row_count):
        df_new = df.iloc[i]
        df_new = pd.DataFrame(df_new, index=None)
        df_new_transpose = df_new.T
        dfs.append(df_new_transpose)
    return dfs


# %%
def fetch_output_range_data_to_csv(
    local_data_base_path: Path,
    start_datetime: datetime,
    end_datetime: datetime,
    timeframe_dict: dict,
    pair_list: list,
):
    try:
        for pair in pair_list:
            for timeframe, timeframe_value in timeframe_dict.items():
                fetch_range_datetime_data_result = fetch_range_datetime_data(
                    pair, timeframe_value, start_datetime, end_datetime
                )
                if is_err(fetch_range_datetime_data_result):
                    return Err(
                        f"{pair}_{timeframe}: {fetch_range_datetime_data_result.err_value}"
                    )
                rates = fetch_range_datetime_data_result.ok_value
                unprocessed_df = pd.DataFrame(rates)
                logger.info(f"fetched {pair}_{timeframe}")
                convert_time_to_datetime_result = convert_time_to_datetime(
                    unprocessed_df
                )
                if is_err(convert_time_to_datetime_result):
                    return Err(
                        f"{pair}_{timeframe}: {convert_time_to_datetime_result.err_value}"
                    )
                temp = convert_time_to_datetime_result.ok_value
                logger.info(f"{pair}_{timeframe} Shape: {temp.shape}")
                dfs = split_df_into_rows(temp)
                for df in dfs:
                    datetime_str = df["datetime"].iloc[0]
                    output_df_to_csv_result = output_df_to_csv(
                        df, pair, timeframe, datetime_str, local_data_base_path
                    )
                    if is_err(output_df_to_csv_result):
                        return Err(output_df_to_csv_result.err_value)
                    output_file = output_df_to_csv_result.ok_value
                    logger.success(f"{pair}_{timeframe}_{output_file} created")
    except Exception as e:
        return Err(f"Error in fetching and output range of data to csv: {e}")
    return Ok("Finish fetching and output range of data to csv")


# %%
def fetch_output_data_to_csv(
    local_data_base_path: Path,
    target_datetime: datetime,
    timeframe_dict: dict,
    pair_list: list,
):
    try:
        for pair in pair_list:
            for timeframe, timeframe_value in timeframe_dict.items():
                fetch_specific_datetime_data_result = fetch_specific_datetime_data(
                    pair, timeframe_value, target_datetime
                )
                if is_err(fetch_specific_datetime_data_result):
                    return Err(
                        f"{pair}_{timeframe}: {fetch_specific_datetime_data_result.err_value}"
                    )
                rates = fetch_specific_datetime_data_result.ok_value
                unprocessed_df = pd.DataFrame(rates)
                logger.info(f"Fetched {pair}_{timeframe}")
                convert_time_to_datetime_result = convert_time_to_datetime(
                    unprocessed_df
                )
                if is_err(convert_time_to_datetime_result):
                    return Err(
                        f"{pair}_{timeframe}: {convert_time_to_datetime_result.err_value}"
                    )
                temp = convert_time_to_datetime_result.ok_value
                logger.info(f"{pair}_{timeframe} Shape: {temp.shape}")
                datetime_str = temp["datetime"].iloc[0]
                output_df_to_csv_result = output_df_to_csv(
                    temp, pair, timeframe, datetime_str, local_data_base_path
                )
                if is_err(output_df_to_csv_result):
                    return Err(output_df_to_csv_result.err_value)
                output_file = output_df_to_csv_result.ok_value
                logger.success(f"{pair}_{timeframe}_{output_file} created")
    except Exception as e:
        return Err(f"Error in fetching and output data to csv: {e}")
    return Ok("Finish fetching and output data to csv")


# %%
def generate_key(filename: str):
    pair, timeframe, date = filename.split("_")
    year, month, day, hour, minute, second = date.split("-")
    return f"{timeframe}/{year}/{month}/{day}/{hour}/{filename}"


# %%
def upload_data_to_s3(
    local_data_base_path: Path, s3_output_base_path: S3Path, pair_list: list
):
    try:
        for pair in pair_list:
            local_file_path = local_data_base_path / pair
            for path in local_file_path.glob("**/*.csv"):
                filename = path.name
                s3_key = generate_key(filename)
                s3_pair_path = s3_output_base_path / pair / s3_key
                s3_pair_path.upload_from(str(path))
                logger.success(f"Successfully uploaded {path} to {s3_pair_path}")
    except Exception as e:
        return Err(f"Error uploading {local_file_path} to {s3_pair_path}: {e}")
    return Ok("Finish uploading")


# %%
def upload_latest_log_to_s3(local_log_path: Path, s3_output_base_path: S3Path):
    log_files = list(local_log_path.glob("*"))
    # get the latest log file and upload it, avoid upload irrelevant log files
    # st_mtime represents the time of the last modification of the file in seconds
    latest_log_file = max(log_files, key=lambda f: f.stat().st_mtime)
    s3_upload_path = s3_output_base_path / "log" / latest_log_file.name
    try:
        s3_upload_path.upload_from(str(latest_log_file))
        return Ok(f"{latest_log_file} uploaded to {s3_output_base_path}")
    except Exception as e:
        return Err(f"Error uploading {latest_log_file} to {s3_output_base_path}: {e}")


# %%
def delete_local_data(local_data_base_path: Path):
    try:
        shutil.rmtree(local_data_base_path)
        logger.success(f"{local_data_base_path} deleted")
    except Exception as e:
        logger.error(f"Error deleting {local_data_base_path}: {e}")


def delete_all_local_data(local_data_base_path, local_log_path):
    logger.info("Deleting local data")
    delete_local_data(local_data_base_path)
    # after delete all data amd catch the log msg, remove the log the upload to S3
    logger.remove()
    delete_local_data(local_log_path)


# %%
def data_fetching_job(config_file_name_str: str):
    # config path
    with open(f"./config/{config_file_name_str}", "r") as file:
        config = yaml.safe_load(file)

    mt5_file_path = Path(config["data_fetching_step"]["mt5_file_path"])
    local_data_base_path = Path(config["data_fetching_step"]["local_data_base_path"])
    s3_output_base_path = S3Path(config["data_fetching_step"]["s3_output_base_path"])
    job_name = config["data_fetching_step"]["job_name"]
    type = config["type"]

    # config datetime
    config_datetime_result = config_datetime(config)
    if is_err(config_datetime_result):
        logger.error(config_datetime_result.err_value)
        return Err(config_datetime_result.err_value)

    if type == "now" or type == "specific_datetime":
        target_datetime = config_datetime_result.ok_value
    elif type == "range":
        start_datetime, end_datetime = (
            config_datetime_result.ok_value[0],
            config_datetime_result.ok_value[1],
        )
    else:
        return Err(
            "Configuring the datetime is not possible due to an invalid input type"
        )

    # config timeframe
    config_timeframe_result = config_timeframe(config)
    if is_err(config_timeframe_result):
        logger.error(config_timeframe_result.err_value)
        return Err(config_timeframe_result.err_value)
    timeframe_dict = config_timeframe_result.ok_value

    # config pair
    config_pair_result = config_pair(config)
    if is_err(config_pair_result):
        logger.error(config_pair_result.err_value)
        return Err(config_pair_result.err_value)
    pair_list = config_pair_result.ok_value

    # config logger
    local_log_path_name = f"{job_name}_logs"
    local_log_path = Path(local_log_path_name)
    create_local_logger(local_log_path_name, job_name)

    # info
    logger.info("The aim of this job: fetch MT5 data")
    logger.info(f"Configuration file name is {config_file_name_str}")
    logger.info(f"Local MT5 data path is ./{local_data_base_path}")
    logger.info(f"Local log path is ./{local_log_path_name}")
    logger.info(f"The type of the datetime is {type}")
    logger.info(f"The target timeframe(s) is/are {timeframe_dict.keys()}")
    logger.info(f"The target pair(s) is/are {pair_list}")

    if type == "now" or type == "specific_datetime":
        logger.info(
            f"The desired target datetime for fetching the MT5 data is {target_datetime}"
        )
    elif type == "range":
        logger.info(
            f"The specified range of datetime for fetching the MT5 data is from {start_datetime} to {end_datetime}."
        )
    else:
        return Err("Invalid input type")
    logger.info(f"The S3 destination of the data and log is {s3_output_base_path}")

    # delete all data before data fetching if old data have not been deleted
    if local_data_base_path.exists():
        logger.info("Clear the MT5 data folder before new data comes in")
        delete_local_data(local_data_base_path)

    # initialize mt5
    logger.info("Trying to initialize MT5")
    initialize_mt5_result = initialize_mt5(mt5_file_path)
    if is_err(initialize_mt5_result):
        logger.error(initialize_mt5_result.err_value)
        upload_latest_log_to_s3(local_log_path, s3_output_base_path)
        return Err(initialize_mt5_result.err_value)
    logger.success(initialize_mt5_result.ok_value)

    # Based on job attribute, fetch data, convert time to datetime, and output to csv
    logger.info("Start fetching MT5 data")
    if type == "now" or type == "specific_datetime":
        result = fetch_output_data_to_csv(
            local_data_base_path, target_datetime, timeframe_dict, pair_list
        )
    elif type == "range":
        result = fetch_output_range_data_to_csv(
            local_data_base_path,
            start_datetime,
            end_datetime,
            timeframe_dict,
            pair_list,
        )
    else:
        return Err(
            "Fetching output data to CSV is not possible due to an invalid input type"
        )
    if is_err(result):
        logger.error(result.err_value)
        upload_latest_log_to_s3(local_log_path, s3_output_base_path)
        return Err(result.err_value)
    logger.success(result.ok_value)

    # upload data
    logger.info("Start uploading fetched data")
    upload_data_to_s3_result = upload_data_to_s3(
        local_data_base_path, s3_output_base_path, pair_list
    )
    if is_err(upload_data_to_s3_result):
        logger.error(upload_data_to_s3_result.err_value)
        return Err(upload_data_to_s3_result.err_value)
    logger.success(upload_data_to_s3_result.ok_value)

    # upload log
    logger.info("Start uploading log")
    upload_latest_log_to_s3_result = upload_latest_log_to_s3(
        local_log_path, s3_output_base_path
    )
    if is_err(upload_latest_log_to_s3_result):
        logger.error(upload_latest_log_to_s3_result.err_value)
        return Err(upload_latest_log_to_s3_result.err_value)
    logger.success(upload_latest_log_to_s3_result.ok_value)

    # delete all data
    delete_all_local_data(local_data_base_path, local_log_path)
    return Ok(f"Finish data fetching job")
