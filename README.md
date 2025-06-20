# Anime Recommendation System

This repository contains the code for an Anime Recommendation System, leveraging MLOps practices for data ingestion, processing, model training, and deployment with Jenkins and Kubernetes.

## Project Setup and Installation

### Conda Environment Setup

To set up your development environment, first activate the specified Conda environment:

```bash
conda activate env/
```

### Install Libraries

Ensure all necessary libraries are installed by running `setup.py`:

```bash
pip install -e .
```

This project defines a custom logger and exception handling for robust operation.

## Google Cloud Platform (GCP) Configuration

To fetch data from a GCP bucket and manage container registries, appropriate service account permissions are required.

### Service Account Permissions

Create a new service account in IAM & Admin -> Service Accounts and assign the following roles:

*   `Cloud Run Admin`
*   `Editor`
*   `Owner`
*   `Service Account User`
*   `Storage Admin`
*   `Storage Object Viewer`
*   `Viewer`

Download the JSON key for this service account from IAM & Admin -> Service Accounts -> Manage keys -> Create new key (JSON). This key will be used for GCP verification during data ingestion, container build/push, and deployment.

Set the path to your GCP service account JSON key file in your `.env` file using the `GOOGLE_APPLICATION_CREDENTIALS` variable.

### Kubernetes Engine Default Node Service Account Permissions

To ensure the default compute service account for Kubernetes can pull images from Google Container Registry (GCR), add the following permissions:

*   `Artifact Registry Reader`
*   `Kubernetes Engine Default Node Service Account`
*   `Storage Object Viewer`

## Data and Model Versioning with DVC

This project utilizes DVC (Data Version Control) for tracking data and model weights.

After training, add the desired folders to DVC:

```bash
dvc init
dvc add folder_name
```

## Application Structure

*   `app.py`: The main Flask application.
*   `templates/index.html`: User interface for the application.
*   `static/style.css`: Styling for the web interface.

The project pipeline includes:

*   `data_ingestion.py`: Fetches data from GCP buckets.
*   `data_processing.py`: Preprocesses the fetched data.
*   `model_training.py`: Handles model training.

## Jenkins CI/CD Setup

This section outlines the steps to set up Jenkins with Docker-in-Docker (DinD) for continuous integration and deployment.

### Prerequisites

*   [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running in the background.

### Jenkins Custom Dockerfile

Create a `custom_jenkins` folder and a `Dockerfile` inside it with the following content:

```dockerfile
# Use the Jenkins image as the base image
FROM jenkins/jenkins:lts

# Switch to root user to install dependencies
USER root

# Install prerequisites and Docker
RUN apt-get update -y && \
    apt-get install -y apt-transport-https ca-certificates curl gnupg software-properties-common && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add - && \
    echo "deb [arch=amd64] https://download.docker.com/linux/debian bullseye stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update -y && \
    apt-get install -y docker-ce docker-ce-cli containerd.io && \
    apt-get clean

# Add Jenkins user to the Docker group (create if it doesn't exist)
RUN groupadd -f docker && \
    usermod -aG docker jenkins

# Create the Docker directory and volume for DinD
RUN mkdir -p /var/lib/docker
VOLUME /var/lib/docker

# Switch back to the Jenkins user
USER jenkins
```

### Build and Run Jenkins Container

Navigate to the `custom_jenkins` directory in your terminal and execute the following commands:

```bash
docker build -t jenkins-dind .
docker images
```

Then, run the Jenkins container:

```bash
docker run -d --name jenkins-dind --privileged -p 8080:8080 -p 50000:50000 -v //var/run/docker.sock:/var/run/docker.sock -v jenkins_home:/var/jenkins_home jenkins-dind
```

Verify the container is running and retrieve the Jenkins administrator password after runnning docker logs:

```bash
docker ps
docker logs jenkins-dind
```

Access Jenkins in your browser at `http://localhost:8080`, paste the password, install suggested plugins, and create your user.

### Jenkins Credentials Configuration

Configure GitHub and GCP credentials in Jenkins:

1.  **GitHub Token**: Go to GitHub -> Settings -> Developer settings -> Personal access tokens -> Tokens (classic) -> Generate new token. Grant `repo` and `admin:repo_hook` permissions.
2.  In Jenkins, navigate to Dashboard -> Manage Jenkins -> Credentials -> Global -> Add Credentials.
    *   Kind: `Username with password`
    *   Username: Your GitHub username
    *   Password: Your GitHub token
    *   ID/Name: `github-token`

3.  **GCP Service Account Key**: In Jenkins, navigate to Dashboard -> Manage Jenkins -> Credentials -> Global -> Add Credentials.
    *   Kind: `Secret file`
    *   Upload the GCP service account JSON file you downloaded earlier.
    *   ID/Name: `gcp-key`

### Configure Jenkins Pipeline

On the Jenkins Dashboard, create a new item:

*   Select `Pipeline`
*   Name the item (e.g., `ml-project-pipeline`)
*   Under `Pipeline` section, choose `Definition` as `Pipeline from SCM`.
*   SCM: `Git`
*   Repository URL: Your GitHub repository link for this project.
*   Credentials: Select `github-token`.
*   Branches to build: Specify your working branch (e.g., `main`).
*   Script Path: `Jenkinsfile` (ensure this file exists in your repository).

### Install GCP CLI and Kubernetes CLI on Jenkins Container

Access the Jenkins container's bash shell as root and install the necessary tools:

```bash
docker exec -u root -it jenkins-dind bash
apt-get update
apt-get install -y curl apt-transport-https ca-certificates gnupg
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
echo "deb https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
apt-get update && apt-get install -y google-cloud-sdk
apt-get install -y kubectl
apt-get install -y google-cloud-sdk-gke-gcloud-auth-plugin
kubectl version --client
gcloud --version
exit
```

Also, install Python and pip within the Jenkins container:

```bash
docker exec -u root -it jenkins-dind bash
apt update -y
apt install -y python3
python3 --version
ln -s /usr/bin/python3 /usr/bin/python
python --version
apt install -y python3-pip
apt install -y python3-venv
exit
```

### Grant Docker Permissions to Jenkins User

From your host machine's terminal (where `custom_jenkins` is located), execute:

```bash
docker exec -u root -it jenkins-dind bash
groupadd docker
usermod -aG docker jenkins
usermod -aG root jenkins
exit
docker restart jenkins-dind
```

Go back to the Jenkins Dashboard and sign in again.

# Now we need to write Dockerfile and Jenkinsfile we will use to build, push and deploy.
## Project Dockerfile

This `Dockerfile` is located in the root of your project and is used to build the application image.

```dockerfile
FROM python:3.11-slim

# Set environment variables to prevent Python from writing .pyc files & Ensure Python output is not buffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required by TensorFlow
RUN apt-get update && apt-get install -y \
    build-essential \
    libatlas-base-dev \
    libhdf5-dev \
    libprotobuf-dev \
    protobuf-compiler \
    python3-dev \
    git \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
    
# Set the working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Install the package in development mode
RUN pip install --no-cache-dir -e .

# Train the model before running the application
RUN python pipeline/training_pipeline.py

# Expose the port that Flask will run on
EXPOSE 5000

# Command to run the app
CMD ["python", "app.py"]
```

**Note**: Replace `mlops-new-447207` with your actual GCP project ID in the image path when building and pushing to GCR.

## Kubernetes Deployment

This `deployment.yaml` file defines the Kubernetes deployment and service for your application.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ml-app
  template:
    metadata:
      labels:
        app: ml-app
    spec:
      containers:
      - name: ml-app-container
        image: gcr.io/(gcp_project_name)/ml-project:latest  # relace project_name with your gcp_project_name
        ports:
        - containerPort: 5000  # Replace with the port your app listens on
---
apiVersion: v1
kind: Service
metadata:
  name: ml-app-service
spec:
  type: LoadBalancer
  selector:
    app: ml-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 5000
```

After pushing everything to GitHub, go to your Jenkins dashboard, select the item you created, and click on `Build Now`. If all configurations are correct, the pipeline should execute successfully.