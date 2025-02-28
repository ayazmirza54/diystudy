import os
import requests
import paramiko
import logging
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set up Paramiko logging
paramiko.util.log_to_file("paramiko.log")

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Get VM configuration from environment variables
VM_IP = os.getenv("VM_IP")
VM_USER = os.getenv("VM_USER", "root")
VM_PASSWORD = os.getenv("VM_PASSWORD")
VM_KEY_PATH = os.getenv("VM_KEY_PATH")
VM_DESTINATION = os.getenv("VM_DESTINATION", "/home/ubuntu")

# Print configuration for debugging
logger.info(f"VM_IP: {VM_IP}")
logger.info(f"VM_USER: {VM_USER}")
logger.info(f"VM_PASSWORD: {'*****' if VM_PASSWORD else 'Not set'}")
logger.info(f"VM_KEY_PATH: {VM_KEY_PATH}")
logger.info(f"VM_DESTINATION: {VM_DESTINATION}")


@app.route("/api/process-github", methods=["POST"])
def process_github():
    data = request.json
    if not data or "github_url" not in data:
        return (
            jsonify(
                {
                    "error": "GitHub URL is required",
                    "example": "https://github.com/username/repo/blob/main/path/to/file.txt",
                }
            ),
            400,
        )

    github_url = data["github_url"]
    logger.info(f"Processing GitHub URL: {github_url}")

    # Convert GitHub URL to raw content URL if needed
    raw_url = convert_to_raw_url(github_url)
    if not raw_url:
        return (
            jsonify(
                {
                    "error": "Invalid GitHub URL format. Please provide a direct link to a file.",
                    "example": "https://github.com/username/repo/blob/main/path/to/file.txt",
                    "provided": github_url,
                }
            ),
            400,
        )

    try:
        # Fetch content from GitHub
        logger.info(f"Fetching content from URL: {raw_url}")
        response = requests.get(raw_url)
        response.raise_for_status()

        # Check if content is binary or text
        content_type = response.headers.get("content-type", "")
        logger.info(f"Content-Type: {content_type}")

        # Detect HTML content (which would indicate we're not getting raw file content)
        if content_type.startswith("text/html"):
            logger.error("Received HTML content instead of raw file content")
            return (
                jsonify(
                    {
                        "error": "Received HTML instead of file content. Please use a direct link to a raw file."
                    }
                ),
                400,
            )

        # Additional check - look for HTML tags in content
        content_preview = response.content[:1000].decode("utf-8", errors="ignore")
        if "<!DOCTYPE html>" in content_preview or "<html" in content_preview:
            logger.error("Content appears to be HTML based on content inspection")
            return (
                jsonify(
                    {
                        "error": "Received HTML instead of file content. Please use a direct link to a raw file."
                    }
                ),
                400,
            )

        # Determine if content is binary or text
        is_binary = not (
            content_type.startswith("text/")
            or content_type.startswith("application/json")
            or content_type.startswith("application/xml")
        )

        # Get content as binary or text
        file_content = response.content if is_binary else response.text

        # Get filename from URL
        filename = os.path.basename(urlparse(raw_url).path)
        logger.info(f"Extracted filename: {filename}")

        # Copy file to VM
        success, message = copy_to_vm(file_content, filename)

        if success:
            return (
                jsonify(
                    {"message": f"Successfully copied {filename} to VM at {VM_IP}"}
                ),
                200,
            )
        else:
            return jsonify({"error": message}), 500

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to fetch GitHub content: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route("/api/clone-and-deploy", methods=["POST"])
def clone_and_deploy():
    data = request.json
    if not data or "github_url" not in data or "project_name" not in data:
        return (
            jsonify(
                {
                    "error": "GitHub URL and project name are required",
                    "example": "https://github.com/username/repo",
                }
            ),
            400,
        )

    github_url = data["github_url"]
    project_name = data["project_name"]

    # Validate GitHub URL format
    if not is_valid_github_repo_url(github_url):
        return (
            jsonify(
                {
                    "error": "Invalid GitHub repository URL format",
                    "example": "https://github.com/username/repo",
                }
            ),
            400,
        )

    try:
        # Clone repository and set up GitHub Pages
        success, message = setup_github_pages(github_url, project_name)

        if success:
            # Extract username and repo name from GitHub URL
            parsed_url = urlparse(github_url)
            path_parts = parsed_url.path.strip("/").split("/")
            username = path_parts[0]
            repo_name = path_parts[1]

            # Generate GitHub Pages URL
            pages_url = f"https://{username}.github.io/{repo_name}"

            return (
                jsonify(
                    {
                        "message": "Repository cloned and GitHub Pages configured successfully",
                        "deployment_url": pages_url,
                        "details": message,
                    }
                ),
                200,
            )
        else:
            return jsonify({"error": message}), 500

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


def convert_to_raw_url(github_url):
    """Convert a GitHub URL to a raw content URL."""
    parsed = urlparse(github_url)

    logger.info(f"Converting GitHub URL: {github_url}")

    # Already a raw URL
    if parsed.netloc == "raw.githubusercontent.com":
        logger.info("Already a raw URL, using as is")
        return github_url

    # Normal GitHub URL
    if parsed.netloc == "github.com":
        path_parts = parsed.path.strip("/").split("/")

        # Check for 'blob' pattern (direct file)
        if len(path_parts) >= 5 and path_parts[2] == "blob":
            # Format: github.com/{owner}/{repo}/blob/{branch}/{path}
            owner = path_parts[0]
            repo = path_parts[1]
            branch = path_parts[3]
            file_path = "/".join(path_parts[4:])
            raw_url = (
                f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
            )
            logger.info(f"Converted blob URL to raw URL: {raw_url}")
            return raw_url

        # Check for 'tree' pattern (directory)
        elif len(path_parts) >= 5 and path_parts[2] == "tree":
            # Directory URLs can't be directly converted to raw content
            logger.error(
                "GitHub URL points to a directory, not a file. Please provide a direct link to a file."
            )
            return None

        logger.warning(f"Could not parse GitHub URL format: {github_url}")
        return (
            None  # Return None instead of the original URL to prevent downloading HTML
        )

    # If the URL is not from GitHub or raw.githubusercontent.com, it's probably invalid
    logger.warning(f"URL is not from GitHub: {github_url}")
    return None


def copy_to_vm(file_content, filename):
    """Copy file content to VM using SSH."""
    if not VM_IP:
        logger.error("VM_IP environment variable not set")
        return False, "VM_IP environment variable not set"

    try:
        logger.info(f"Attempting to connect to VM at {VM_IP} with user {VM_USER}")

        # Set up SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connected = False

        # Try to connect using key file if provided
        if VM_KEY_PATH:
            logger.info(f"Attempting to connect using key file at path: {VM_KEY_PATH}")
            try:
                # Check if key file exists
                if not os.path.exists(VM_KEY_PATH):
                    logger.error(f"Key file does not exist: {VM_KEY_PATH}")
                    return False, f"Key file does not exist: {VM_KEY_PATH}"

                # Try RSA key first
                try:
                    logger.info("Trying to load as RSA key")
                    private_key = paramiko.RSAKey.from_private_key_file(VM_KEY_PATH)
                    ssh.connect(VM_IP, username=VM_USER, pkey=private_key, timeout=10)
                    connected = True
                    logger.info("Connected using RSA key")
                except Exception as rsa_error:
                    logger.warning(f"Failed to connect with RSA key: {str(rsa_error)}")

                    # Try Ed25519 key if RSA fails
                    try:
                        logger.info("Trying to load as Ed25519 key")
                        private_key = paramiko.Ed25519Key.from_private_key_file(
                            VM_KEY_PATH
                        )
                        ssh.connect(
                            VM_IP, username=VM_USER, pkey=private_key, timeout=10
                        )
                        connected = True
                        logger.info("Connected using Ed25519 key")
                    except Exception as ed_error:
                        logger.warning(
                            f"Failed to connect with Ed25519 key: {str(ed_error)}"
                        )
                        # Let the next authentication method try
            except Exception as e:
                logger.error(f"Error with key file: {str(e)}")
                return False, f"Error with key file: {str(e)}"

        # Try password if key didn't work
        if not connected and VM_PASSWORD:
            logger.info("Attempting to connect using password")
            try:
                ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=10)
                connected = True
                logger.info("Connected using password")
            except Exception as e:
                logger.error(f"Failed to connect with password: {str(e)}")
                # Continue to error handling

        # If we didn't connect with either method
        if not connected:
            logger.error("Failed to connect via any method")
            return (
                False,
                "Failed to authenticate with VM. Check VM_KEY_PATH or VM_PASSWORD",
            )

        logger.info("Successfully connected to VM, creating SFTP client")

        # Create SFTP client
        sftp = ssh.open_sftp()

        # Create temporary file locally using platform-appropriate temp directory
        import tempfile

        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, filename)

        # Determine write mode based on content type
        is_binary = isinstance(file_content, bytes)
        write_mode = "wb" if is_binary else "w"

        logger.info(f"Writing temporary file to {temp_path}")
        with open(temp_path, write_mode) as f:
            f.write(file_content)

        # Ensure destination directory exists
        destination = f"{VM_DESTINATION}/{filename}"
        logger.info(f"Copying file to VM path: {destination}")

        try:
            # Check directory permissions
            try:
                stdin, stdout, stderr = ssh.exec_command(f"ls -la {VM_DESTINATION}")
                output = stdout.read().decode("utf-8")
                error = stderr.read().decode("utf-8")
                logger.info(f"Destination directory listing: {output}")
                if error:
                    logger.warning(f"Error listing destination directory: {error}")

                # Check if we can write to the directory
                test_file = f"{VM_DESTINATION}/.write_test"
                stdin, stdout, stderr = ssh.exec_command(
                    f"touch {test_file} && rm {test_file}"
                )
                exit_status = stdout.channel.recv_exit_status()
                if exit_status != 0:
                    error = stderr.read().decode("utf-8")
                    logger.warning(f"Permission test failed: {error}")
                else:
                    logger.info("Write permission test succeeded")
            except Exception as e:
                logger.warning(f"Failed to check directory permissions: {str(e)}")

            # Try to create destination directory
            try:
                stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {VM_DESTINATION}")
                exit_status = stdout.channel.recv_exit_status()
                if exit_status != 0:
                    error = stderr.read().decode("utf-8")
                    logger.warning(f"Warning creating destination directory: {error}")
            except Exception as e:
                logger.warning(f"Failed to create destination directory: {str(e)}")

            # Copy file to VM with detailed error handling
            try:
                logger.info(
                    f"Starting SFTP put operation: {temp_path} -> {destination}"
                )
                sftp.put(temp_path, destination)
                logger.info("File successfully copied to VM")
            except IOError as e:
                logger.error(f"SFTP IOError: {str(e)}")
                # Try to get additional context about the destination
                try:
                    stdin, stdout, stderr = ssh.exec_command(f"stat {VM_DESTINATION}")
                    output = stdout.read().decode("utf-8")
                    logger.info(f"Destination stat: {output}")
                except Exception as stat_err:
                    logger.error(f"Failed to get directory stats: {str(stat_err)}")
                return (
                    False,
                    f"SFTP IOError: {str(e)}. Please check if the destination directory exists and has correct permissions.",
                )
            except Exception as e:
                logger.error(f"SFTP error: {str(e)}")
                return False, f"SFTP error: {str(e)}"

        except Exception as e:
            logger.error(f"SFTP operation failed: {str(e)}")
            return False, f"SFTP operation failed: {str(e)}"
        finally:
            # Clean up
            try:
                os.remove(temp_path)
                logger.info("Temporary file removed")
            except Exception as e:
                logger.warning(f"Could not remove temporary file: {str(e)}")

            sftp.close()
            ssh.close()
            logger.info("SSH connection closed")

        return True, "File copied successfully"
    except Exception as e:
        logger.error(f"Error copying file to VM: {str(e)}")
        return False, f"Error copying file to VM: {str(e)}"


def is_valid_github_repo_url(url):
    """Validate GitHub repository URL format."""
    pattern = r"^https?://github\.com/[\w-]+/[\w.-]+/?$"
    return bool(re.match(pattern, url))


def setup_github_pages(github_url, project_name):
    """Clone repository and set up GitHub Pages deployment."""
    try:
        if not VM_IP:
            return False, "VM_IP environment variable not set"

        # Set up SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to VM (reusing existing connection logic)
        connected = False
        if VM_KEY_PATH:
            try:
                private_key = paramiko.RSAKey.from_private_key_file(VM_KEY_PATH)
                ssh.connect(VM_IP, username=VM_USER, pkey=private_key)
                connected = True
            except:
                try:
                    private_key = paramiko.Ed25519Key.from_private_key_file(VM_KEY_PATH)
                    ssh.connect(VM_IP, username=VM_USER, pkey=private_key)
                    connected = True
                except:
                    pass

        if not connected and VM_PASSWORD:
            ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD)
            connected = True

        if not connected:
            return False, "Failed to authenticate with VM"

        # Create project directory
        project_dir = f"{VM_DESTINATION}/{project_name}"
        commands = [
            f"mkdir -p {project_dir}",
            f"cd {project_dir}",
            f"git clone {github_url} .",
            "npm install",  # Install dependencies
            # Create GitHub Actions workflow for Pages deployment
            "mkdir -p .github/workflows",
            """cat > .github/workflows/deploy.yml << 'EOL'
name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '16'
          
      - name: Install Dependencies
        run: npm install
        
      - name: Build
        run: npm run build
        
      - name: Deploy to GitHub Pages
        uses: JamesIves/github-pages-deploy-action@4.1.5
        with:
          branch: gh-pages
          folder: build
EOL""",
            # Update package.json with homepage field
            f"""sed -i '/"name"/a \  "homepage": "{github_url}",' package.json""",
            # Commit and push changes
            "git add .",
            'git config --global user.email "deploy@example.com"',
            'git config --global user.name "Deployment Bot"',
            'git commit -m "Configure GitHub Pages deployment"',
            "git push",
        ]

        # Execute commands
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                error = stderr.read().decode("utf-8")
                return False, f"Command failed: {cmd}\nError: {error}"

        ssh.close()
        return True, "Repository cloned and GitHub Pages configured successfully"

    except Exception as e:
        return False, f"Error setting up GitHub Pages: {str(e)}"


# Add application-level error handler
@app.errorhandler(500)
def internal_error(error):
    import traceback

    logger.error(f"500 error: {error}")
    logger.error(traceback.format_exc())
    return jsonify({"error": "Internal server error", "details": str(error)}), 500


if __name__ == "__main__":
    logger.info("========================= STARTING SERVER =========================")
    logger.info(
        f"Configuration: VM_IP={VM_IP}, VM_USER={VM_USER}, VM_KEY_PATH={VM_KEY_PATH}"
    )
    logger.info("Make sure to set the environment variables in the .env file")
    logger.info(
        "If using key authentication, ensure key file exists and has correct permissions"
    )
    logger.info("==================================================================")
    app.run(debug=True, host="0.0.0.0", port=5000)
