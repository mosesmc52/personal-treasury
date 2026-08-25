"""Small Amazon SES wrapper retained from the original project."""
import boto3


class AmazonSES:
    def __init__(self, region, access_key, secret_key, from_address, charset="UTF-8"):
        self.CHARSET = charset
        self.from_address = from_address
        self.client = boto3.client("ses", region_name=region, aws_access_key_id=access_key, aws_secret_access_key=secret_key)

    def send_text_email(self, to_address, subject, content):
        return self.client.send_email(Destination={"ToAddresses": [to_address]}, Message={"Body": {"Text": {"Charset": self.CHARSET, "Data": content}}, "Subject": {"Charset": self.CHARSET, "Data": subject}}, Source=self.from_address)

    def send_html_email(self, to_address, subject, content):
        return self.client.send_email(Destination={"ToAddresses": [to_address]}, Message={"Body": {"Html": {"Charset": self.CHARSET, "Data": content}}, "Subject": {"Charset": self.CHARSET, "Data": subject}}, Source=self.from_address)

