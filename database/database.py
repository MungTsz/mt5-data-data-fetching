import boto3
import json
from result import Result, Ok, Err
from sqlalchemy import create_engine
from botocore.exceptions import ClientError


def get_database_credentials(secret_name, profile_name) -> Result[dict, str]:
    REGION = "ap-southeast-1"
    session = boto3.session.Session(profile_name=profile_name)
    client = session.client(service_name="secretsmanager", region_name=REGION)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        return Err(e.response["Error"]["Code"])

    secret_str = get_secret_value_response["SecretString"]
    secret_dict = json.loads(secret_str)
    return Ok(secret_dict)


def get_database_engine(
    secret_name="RDS_database",
    profile_name="data-storage-administrator-440197809615",
    database_name="MT5_test_data",
) -> Result[object, str]:
    database_credentials_result = get_database_credentials(secret_name, profile_name)

    if database_credentials_result.is_err():
        return Err(
            f"Get database credentials error :{database_credentials_result.err_value}"
        )

    database_credentials_dict = database_credentials_result.ok_value

    endpoint = database_credentials_dict["host"]
    port = database_credentials_dict["port"]
    user_name = database_credentials_dict["username"]
    password = database_credentials_dict["password"]

    engine = create_engine(
        f"mysql+pymysql://{user_name}:{password}@{endpoint}:{port}/{database_name}"
    )

    try:
        engine.connect()
    except Exception as e:
        print(f"ERROR: Unexpected error: Could not connect to MySQL instance. {e}")
        return Err(e)
    print("SUCCESS: Connection to RDS MySQL instance succeeded")
    return Ok(engine)
