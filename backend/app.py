import os
import requests
import logging
import re
import shutil
import subprocess
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Local destination directory
LOCAL_DESTINATION = os.getenv("LOCAL_DESTINATION", "/var/www/html")

# Print configuration for debugging
logger.info(f"LOCAL_DESTINATION: {LOCAL_DESTINATION}")


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

        # Save file locally
        success, message = save_file_locally(file_content, filename)

        if success:
            return (
                jsonify(
                    {"message": f"Successfully saved {filename} to local destination"}
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
        # Clone repository locally
        success, message = clone_repo_locally(github_url, project_name)

        if success:
            # Extract username and repo name from GitHub URL
            parsed_url = urlparse(github_url)
            path_parts = parsed_url.path.strip("/").split("/")
            username = path_parts[0]
            repo_name = path_parts[1]

            # Generate GitHub Pages URL (just for compatibility with old code)
            pages_url = f"https://{username}.github.io/{repo_name}"

            return (
                jsonify(
                    {
                        "message": "Repository cloned successfully",
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


def save_file_locally(file_content, filename):
    """Save file content to the local destination directory."""
    try:
        # Ensure the destination directory exists
        os.makedirs(LOCAL_DESTINATION, exist_ok=True)
        
        # Construct the full destination path
        destination = os.path.join(LOCAL_DESTINATION, filename)
        logger.info(f"Saving file to: {destination}")
        
        # Determine write mode based on content type
        is_binary = isinstance(file_content, bytes)
        write_mode = "wb" if is_binary else "w"
        
        # Write the file
        with open(destination, write_mode) as f:
            f.write(file_content)
            
        logger.info(f"File successfully saved to {destination}")
        return True, f"File saved successfully to {destination}"
    
    except Exception as e:
        logger.error(f"Error saving file locally: {str(e)}")
        return False, f"Error saving file locally: {str(e)}"


def is_valid_github_repo_url(url):
    """Validate GitHub repository URL format."""
    pattern = r"^https?://github\.com/[\w-]+/[\w.-]+/?$"
    return bool(re.match(pattern, url))


def clone_repo_locally(github_url, project_name):
    """Clone repository locally."""
    try:
        # Create project directory
        project_dir = os.path.join(LOCAL_DESTINATION, project_name)
        logger.info(f"Cloning repository to: {project_dir}")
        
        # Create directory if it doesn't exist
        os.makedirs(project_dir, exist_ok=True)
        
        # Check if directory is empty
        if os.listdir(project_dir):
            logger.warning(f"Directory {project_dir} is not empty, clearing it")
            # Clear directory content
            for item in os.listdir(project_dir):
                item_path = os.path.join(project_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
        
        # Clone the repository
        result = subprocess.run(
            ["git", "clone", github_url, "."],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            logger.error(f"Git clone failed: {result.stderr}")
            return False, f"Git clone failed: {result.stderr}"
        
        logger.info(f"Repository cloned successfully to {project_dir}")
        
        # Try to run npm install if package.json exists
        if os.path.exists(os.path.join(project_dir, "package.json")):
            logger.info("package.json found, running npm install")
            npm_result = subprocess.run(
                ["npm", "install"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                check=False
            )
            
            if npm_result.returncode != 0:
                logger.warning(f"npm install warning: {npm_result.stderr}")
            else:
                logger.info("npm install completed successfully")
        
        return True, f"Repository cloned successfully to {project_dir}"
    
    except Exception as e:
        logger.error(f"Error cloning repository: {str(e)}")
        return False, f"Error cloning repository: {str(e)}"


# Add application-level error handler
@app.errorhandler(500)
def internal_error(error):
    import traceback

    logger.error(f"500 error: {error}")
    logger.error(traceback.format_exc())
    return jsonify({"error": "Internal server error", "details": str(error)}), 500


if __name__ == "__main__":
    logger.info("========================= STARTING SERVER =========================")
    logger.info(f"Configuration: LOCAL_DESTINATION={LOCAL_DESTINATION}")
    logger.info("Make sure LOCAL_DESTINATION directory exists and has write permissions")
    logger.info("==================================================================")
    app.run(debug=True, host="0.0.0.0", port=5000)