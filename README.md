# GitHub to VM Deployment Tool

A web application that allows you to deploy files from GitHub to a VM with a configurable IP address.

## Project Structure

- **Frontend**: React application with TypeScript and Tailwind CSS
- **Backend**: Flask API that fetches content from GitHub and transfers it to the VM via SSH

## Setup

### Prerequisites

- Python 3.7+
- Node.js 14+
- npm or yarn
- Access to a VM with SSH connectivity

### Configuration

1. Copy the example environment file and configure your VM settings:
   ```
   cd backend
   cp .env.example .env
   ```

2. Edit the `.env` file with your VM credentials:
   ```
   VM_IP=your_vm_ip_address
   VM_USER=your_vm_username
   VM_PASSWORD=your_vm_password
   # OR use key-based authentication
   # VM_KEY_PATH=/path/to/private_key
   VM_DESTINATION=/path/on/vm/to/store/files
   ```

## Running the Application

### Windows

Simply run the start script:
```
start.bat
```

### Linux/macOS

Make the script executable and run it:
```
chmod +x start.sh
./start.sh
```

### Manual Start

1. Start the backend:
   ```
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```

2. Start the frontend:
   ```
   cd frontend
   npm install
   npm run dev
   ```

## Usage

1. Open your browser and navigate to http://localhost:5173 (or the port shown in the frontend terminal)
2. Enter a project name (optional)
3. Paste a GitHub URL for the file you want to deploy (must be a direct link to a file)
4. Click DEPLOY
5. The file will be downloaded from GitHub and copied to your configured VM

## API Endpoints

- **POST /api/process-github**
  - Request Body: `{ "github_url": "https://github.com/user/repo/blob/branch/path/to/file.txt" }`
  - Response: `{ "message": "Successfully copied file.txt to VM at 10.0.0.1" }` or `{ "error": "Error message" }`

## Troubleshooting

- If the frontend can't connect to the backend, check that the Flask server is running on port 5000
- Ensure your VM is accessible via SSH from the machine running the backend
- Check the backend logs for any SSH connection errors