# Test Automation

Simple test automation for validating the automation manager.

## Overview

This automation is used exclusively for testing the automation lifecycle:
- Discovery
- Validation
- Installation
- Enabling
- Disabling
- Uninstallation

## Workflow

The workflow consists of:
1. **Manual Trigger** - Starts the workflow manually
2. **Set Result** - Returns a success message

## Requirements

- No external credentials required
- No external services required

## Testing

This automation is used to test:
- `discover` - Automation discovery
- `validate` - Manifest validation
- `install` - Installation flow
- `get` - Retrieval
- `enable` - Activation
- `disable` - Deactivation
- `uninstall` - Removal