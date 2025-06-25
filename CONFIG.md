# Configuration Management

This project uses centralized configuration to avoid hardcoded values across scripts.

## Configuration File

All configuration values are centralized in `config.sh`. This file contains:

- **AWS Configuration**: Profile and region settings
- **KMS Configuration**: Key alias and description
- **Pulumi Configuration**: Stack name, S3 backend, and secrets provider
- **Project Configuration**: Name and tags

## Usage

All scripts automatically source the configuration by including:

```bash
# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"
```

## Updating Configuration

To change configuration values:

1. Edit `config.sh`
2. Update the desired values
3. The changes will automatically be used by all scripts

## Available Configuration Variables

- `AWS_PROFILE`: AWS CLI profile to use
- `AWS_REGION`: AWS region for resources
- `KMS_KEY_ALIAS`: KMS key alias for Pulumi secrets
- `PULUMI_STACK_NAME`: Name of the Pulumi stack
- `PULUMI_S3_BACKEND`: S3 bucket for Pulumi state
- `PROJECT_NAME`: Project name for tagging

## Helper Functions

The configuration file also provides helper functions:

- `check_aws_profile()`: Verify AWS profile is accessible
- `check_kms_key()`: Verify KMS key exists and is accessible
- `show_config()`: Display current configuration values

## Benefits

- **Single Source of Truth**: All configuration in one place
- **Consistency**: Same values used across all scripts
- **Maintainability**: Easy to update configuration
- **Flexibility**: Easy to switch between environments
