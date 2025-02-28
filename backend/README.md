# GitHub to VM File Transfer Backend

A Flask backend that provides an API endpoint to fetch files from GitHub and copy them to a VM with a configurable IP address.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Edit the values to match your VM configuration:
     - `VM_IP`: IP address of your VM (required)
     - `VM_USER`: SSH username (default: root)
     - `VM_PASSWORD`: SSH password (required if not using key authentication)
     - `VM_KEY_PATH`: Path to SSH private key (required if not using password)
     - `VM_DESTINATION`: Path on VM where files should be saved (default: /tmp)

3. Start the server:
   ```
   python app.py
   ```

## API Endpoint

### POST /api/process-github

Process a GitHub URL, fetch its content, and copy it to the configured VM.

**Request body**:
```json
{
  "github_url": "https://github.com/username/repo/blob/branch/path/to/file.txt"
}
```

**Response (success)**:
```json
{
  "message": "Successfully copied file.txt to VM at 10.0.0.1"
}
```

**Response (error)**:
```json
{
  "error": "Error message"
}
```

## Notes

- The API accepts GitHub URLs in the standard format (`https://github.com/username/repo/blob/branch/path/to/file.txt`) and automatically converts them to raw content URLs.
- Files are transferred to the VM using SSH/SFTP.
- CORS is enabled to allow requests from any origin.