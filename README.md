# FileFlux Worker Web Application

## Overview
This is a backend Python Flask-based web application designed receive, process and save files from the end users. The application is designed to be deployed in a Kubernetes cluster and uses a CockroachDB Cluster as the backend database for storing information and uses ZFS pools across various Kubernetes worker nodes to store the end-user files. Note that this is the worker application that interacts with the FileFlux Manager Web Application and does the actual processing of files using the ZFS pools and CockroachDB Cluster and it will not work as a standalone application.

## Features
- Interaction with the FileFlux Manager to process files from end users and save them to ZFS pools on various Kubernetes worker nodes.
- Interacts with CockroachDB Cluster to save various information like user details, bucket details, file details, location on the worker nodes etc.
- Includes custom readiness and liveness probes for Kubernetes to ensure high availability.
- GitHub Actions CI/CD workflow to build a multi-platform container image and push it to DockerHub.
- Integrated security scanning of the container image using Trivy.

## Prerequisites
To run this application locally or in a container, you need:
- Python 3.11+
- Flask
- CockroachDB Cluster (for database interactions)
- Docker (for containerization)

Install the dependencies locally by running:
```bash
pip install -r requirements.txt
```

## Repository Structure

```plaintext
fileflux-manager-webapp/             
├── Dockerfile              
├── README.md               
├── app.py                  
├── db.py                  
├── liveness.sh             
├── readiness.sh            
├── requirements.txt   
```

### What Each File Does
- **docker.yaml**: Contains the GitHub Actions workflow for building and pushing the multi-platform container image to DockerHub and scanning it for vulnerabilities using Trivy.

- **app.py**: The core of the web application. It receives requests from the FileFlux Manager and processes them in conjunction with the CockroachDB Cluster and ZFS pools on the worker nodes.
  
- **db.py**: Handles database connections, using CockroachDB as the backend database for storing node information.

- **liveness.sh**: A script used for Kubernetes' liveness probe, checking whether the app is running and responsive.

- **readiness.sh**: A script for Kubernetes' readiness probe, ensuring the app is ready to serve requests.

- **requirements.txt**: Specifies the Python dependencies required to run the web application (Flask, PostgreSQL connector, etc.), to be installed while building the container image.

- **Dockerfile**: Configuration for building the web app Docker image. It sets up the necessary Python environment, installs dependencies, and configures health checks.

## Building a Docker Image

To build the Docker image for this web app:

1. Clone the repository:
   ```bash
   git clone https://github.com/fileflux/worker-webapp.git
   cd worker-webapp
   ```

2. Build the Docker image:
   ```bash
   docker build -t worker-webapp .
   ```

## Probes

This web app includes Kubernetes health probes:

- **Liveness Probe**: Ensures that the container is still running. If this probe fails, Kubernetes will restart the container.
  ```bash
  ./liveness.sh
  ```

- **Readiness Probe**: Ensures that the app is ready to serve traffic. If this probe fails, Kubernetes will stop sending requests to the container.
  ```bash
  ./readiness.sh
  ```

Both scripts are designed to return appropriate status codes to Kubernetes based on the application’s health.

## GitHub Workflow (including Trivy)

A GitHub Actions workflow is included to automate the build process. The workflow builds a multi-platform container image using Docker for AMD64 and ARM based systems and pushes the image to DockerHub. This workflow also integrates `Trivy`, a vulnerability scanning tool to scan the aforementioned container image, to ensure that it is secure.

This workflow:
1. Checks the code and accesses DockerHub.
2. Builds and pushes multi-platform Docker images for AMD64 and ARM to DockerHub using the Dockerfile in the repository.
3. Runs a security scan on the Docker image using `Trivy`.
4. Logs out from DockerHub.

## Additional Notes
- Ensure that the CockroachDB cluster is set up and running before starting the web application. You can modify the database connection in `db.py` to match your configuration.
- The liveness and readiness probes are useful when deploying the app in a Kubernetes environment to ensure high availability.
