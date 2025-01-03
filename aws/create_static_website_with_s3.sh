#!/usr/bin/env bash

# This script creates a static website using S3 as a storage backend.
# It uses the AWS CLI to create the S3 bucket and upload template files
# It creates a folder in ~/projects/$BUCKET_NAME and uploads the files to it

if [ -z "$1" ]; then
    echo "Usage: $0 <bucket-name>"
    exit 1
fi

BUCKET_NAME="$1"

aws s3 mb s3://$BUCKET_NAME
aws s3api put-public-access-block --bucket $BUCKET_NAME --public-access-block-configuration BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false
aws s3 website s3://$BUCKET_NAME --index-document index.html --error-document error.html
mk ~/projects/$BUCKET_NAME
echo "<html><body><h1>Hello World</h1></body></html>" > ~/projects/$BUCKET_NAME/index.html
echo "<html><body><h1>Error</h1></body></html>" > ~/projects/$BUCKET_NAME/error.html
aws s3 cp --recursive ~/projects/$BUCKET_NAME s3://$BUCKET_NAME

cat <<EOF > ~/projects/$BUCKET_NAME/policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/*"
    }
  ]
}
EOF

aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy file://~/projects/$BUCKET_NAME/policy.json

echo "http://$BUCKET_NAME.s3-website-us-east-1.amazonaws.com"
