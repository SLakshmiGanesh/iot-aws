import os

os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("TABLE_NAME", "telemetry-test")
os.environ.setdefault("DEVICES_TABLE_NAME", "devices-test")
os.environ.setdefault("HOME_ID", "home-test")

from cloud_lambda_placeholder import unused
