# Kimigayo OS - Cloud Deployment Guide

This guide explains how to run containers built on Kimigayo OS on a VPS and on major cloud platforms.

## What you deploy

Kimigayo OS is a **base image**, not an application. The published image
(`ishinokazuki/kimigayo-os`) contains only a rootfs (musl, BusyBox, OpenRC);
there is no kernel in it, and its default command is `/bin/sh`. If you deploy
the bare image, the container starts a shell and exits immediately (nothing
listens on a port, nothing answers a health check).

So every example below assumes **your own application image built on top of
Kimigayo**:

```dockerfile
FROM ishinokazuki/kimigayo-os:3.1.0-standard
# Copy your application (and the shared libraries it needs; see
# examples/python/Dockerfile for collecting them with ldd)
COPY --from=build /out/my-app /usr/local/bin/my-app
EXPOSE 8080
CMD ["/usr/local/bin/my-app"]
```

```bash
docker build -t my-app:1.0.0 .
```

- Pin the Kimigayo version (`3.1.0-standard`) or a digest; `latest` moves on every release
- Minimal has no `wget`; use Standard or Extended if your health check needs it
- Your application should handle SIGTERM; otherwise every stop waits for the
  platform's grace period (see [lifecycle.md](../benchmarks/lifecycle.md))

The intended use is **Docker on a VPS**. Managed container services also work,
because they run the same image. Booting Kimigayo as a VM image (AMI, cloud
images, bare metal) is not supported: the image has no kernel or bootloader.

## Table of Contents

- [VPS (Docker)](#vps)
- [AWS (Amazon Web Services)](#aws)
- [Azure (Microsoft Azure)](#azure)
- [GCP (Google Cloud Platform)](#gcp)
- [Best Practices](#best-practices)

---

<a name="vps"></a>

## VPS (Docker)

```bash
# On the VPS
docker pull registry.example.com/my-app:1.0.0
docker run -d --name my-app --restart unless-stopped \
  -p 80:8080 registry.example.com/my-app:1.0.0
```

With Compose (`compose.yaml`):

```yaml
services:
  my-app:
    image: registry.example.com/my-app:1.0.0
    restart: unless-stopped
    ports:
      - "80:8080"
```

```bash
docker compose up -d
```

---

<a name="aws"></a>

## AWS (Amazon Web Services)

### Container Deployment

#### Amazon ECS (Elastic Container Service)

**1. Push image to ECR**

```bash
# Authenticate to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.us-east-1.amazonaws.com

# Tag image
docker tag my-app:1.0.0 \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:1.0.0

# Push image
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:1.0.0
```

**2. Create ECS Task Definition**

```json
{
  "family": "my-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "my-app",
      "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:1.0.0",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/my-app",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "wget -q --spider http://localhost:8080/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

The CPU/memory values are examples; size them for your application.
The health check assumes your app serves `/health` and the image is Standard or
Extended (Minimal has no `wget`).

**3. Deploy with AWS CLI**

```bash
# Create service
aws ecs create-service \
  --cluster my-cluster \
  --service-name my-app \
  --task-definition my-app:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration \
    "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
```

#### Amazon EKS (Elastic Kubernetes Service)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-app
        image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:1.0.0
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
---
apiVersion: v1
kind: Service
metadata:
  name: my-app
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
```

---

<a name="azure"></a>

## Azure (Microsoft Azure)

### Container Deployment

#### Azure Container Instances (ACI)

**1. Push image to ACR**

```bash
# Login to ACR
az acr login --name myregistry

# Tag image
docker tag my-app:1.0.0 myregistry.azurecr.io/my-app:1.0.0

# Push image
docker push myregistry.azurecr.io/my-app:1.0.0
```

**2. Deploy to ACI**

```bash
az container create \
  --resource-group myResourceGroup \
  --name my-app \
  --image myregistry.azurecr.io/my-app:1.0.0 \
  --cpu 1 \
  --memory 1 \
  --registry-login-server myregistry.azurecr.io \
  --registry-username <username> \
  --registry-password <password> \
  --dns-name-label my-app \
  --ports 8080
```

**3. Using ARM Template**

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "resources": [
    {
      "type": "Microsoft.ContainerInstance/containerGroups",
      "apiVersion": "2021-09-01",
      "name": "my-app-group",
      "location": "[resourceGroup().location]",
      "properties": {
        "containers": [
          {
            "name": "my-app",
            "properties": {
              "image": "myregistry.azurecr.io/my-app:1.0.0",
              "resources": {
                "requests": {
                  "cpu": 1,
                  "memoryInGb": 1
                }
              },
              "ports": [
                {
                  "port": 8080,
                  "protocol": "TCP"
                }
              ]
            }
          }
        ],
        "osType": "Linux",
        "ipAddress": {
          "type": "Public",
          "ports": [
            {
              "protocol": "TCP",
              "port": 8080
            }
          ]
        }
      }
    }
  ]
}
```

#### Azure Kubernetes Service (AKS)

```bash
# Create AKS cluster
az aks create \
  --resource-group myResourceGroup \
  --name my-cluster \
  --node-count 3 \
  --node-vm-size Standard_B2s \
  --generate-ssh-keys

# Get credentials
az aks get-credentials \
  --resource-group myResourceGroup \
  --name my-cluster

# Deploy (same Kubernetes manifests as EKS, with the image path changed)
kubectl apply -f deployment.yaml
```

---

<a name="gcp"></a>

## GCP (Google Cloud Platform)

Container Registry (`gcr.io`) has been replaced by **Artifact Registry**.
The examples use Artifact Registry.

### Container Deployment

#### Cloud Run

**1. Push image to Artifact Registry**

```bash
# Create a Docker repository (once)
gcloud artifacts repositories create my-repo \
  --repository-format=docker --location=us-central1

# Configure Docker for Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Tag image
docker tag my-app:1.0.0 \
  us-central1-docker.pkg.dev/my-project/my-repo/my-app:1.0.0

# Push image
docker push us-central1-docker.pkg.dev/my-project/my-repo/my-app:1.0.0
```

**2. Deploy to Cloud Run**

Cloud Run requires the container to listen on the port given by `--port`
(your application must do this; the bare Kimigayo image does not).

```bash
gcloud run deploy my-app \
  --image us-central1-docker.pkg.dev/my-project/my-repo/my-app:1.0.0 \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --port 8080 \
  --max-instances 10 \
  --min-instances 1
```

**3. Using YAML**

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: my-app
spec:
  template:
    spec:
      containers:
      - image: us-central1-docker.pkg.dev/my-project/my-repo/my-app:1.0.0
        ports:
        - containerPort: 8080
        resources:
          limits:
            memory: 512Mi
            cpu: "1"
```

Deploy:
```bash
gcloud run services replace service.yaml
```

#### Google Kubernetes Engine (GKE)

```bash
# Create GKE cluster
gcloud container clusters create my-cluster \
  --num-nodes 3 \
  --machine-type e2-small \
  --region us-central1

# Get credentials
gcloud container clusters get-credentials my-cluster \
  --region us-central1

# Deploy (same Kubernetes manifests, with the image path changed)
kubectl apply -f deployment.yaml
```

---

<a name="best-practices"></a>

## Best Practices

### Security

#### 1. Use Private Container Registries

```bash
# AWS ECR
aws ecr create-repository --repository-name my-app

# Azure ACR
az acr create --resource-group myRG --name myregistry --sku Basic

# GCP Artifact Registry
gcloud artifacts repositories create my-repo \
  --repository-format=docker --location=us-central1
```

#### 2. Implement Least Privilege

**AWS IAM Policy Example:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability"
      ],
      "Resource": "arn:aws:ecr:*:*:repository/my-app"
    }
  ]
}
```

#### 3. Vulnerability Scanning

Registry scanners (ECR image scanning, Microsoft Defender for Containers,
Artifact Analysis) identify components from a package database. **Kimigayo has
no package database, so these scanners cannot see the Kimigayo layer** (the same
is true of Trivy's image scan). They still scan what your application adds
(for example language packages).

To check the Kimigayo components themselves, use the project's scanner, which
reads versions out of the binaries and matches them against CVEs:

```bash
# In a clone of the Kimigayo repository
bash scripts/scan-image.sh ishinokazuki/kimigayo-os:3.1.0-standard standard x86_64
```

The published images are also checked weekly (`published-image-cve-scan.yml`), and
each GitHub Release carries a CycloneDX SBOM per image.

### Cost Optimization

#### 1. Right-Size Resources

Kimigayo itself uses a few hundred KB of memory (288KB resident for an idle
Standard container, v3.0.2). The resources you need are determined by your
application; measure it and size accordingly.

#### 2. Use Spot/Preemptible Capacity

**AWS Fargate Spot:**
```json
{
  "capacityProviders": ["FARGATE", "FARGATE_SPOT"],
  "defaultCapacityProviderStrategy": [
    {
      "capacityProvider": "FARGATE_SPOT",
      "weight": 2,
      "base": 0
    },
    {
      "capacityProvider": "FARGATE",
      "weight": 1,
      "base": 1
    }
  ]
}
```

**GKE Spot Nodes:**
```bash
gcloud container node-pools create spot-pool \
  --cluster my-cluster \
  --region us-central1 \
  --spot \
  --num-nodes 3
```

#### 3. Auto-scaling

**AWS ECS:**
```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/my-cluster/my-app \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 1 \
  --max-capacity 10
```

**GCP Cloud Run (automatic):**
```bash
gcloud run services update my-app \
  --region us-central1 \
  --min-instances 0 \
  --max-instances 10
```

### Monitoring

#### AWS CloudWatch

```bash
# View logs
aws logs tail /ecs/my-app --follow
```

#### Azure Monitor

```bash
# View logs
az monitor log-analytics query \
  --workspace <workspace-id> \
  --analytics-query "ContainerLog | where Name == 'my-app'"
```

#### GCP Cloud Logging

```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=my-app"
```

### Versioning

Tag your own images with an explicit version, and pin the Kimigayo base image
the same way. Kimigayo's own tags look like `3.1.0`, `3.1.0-standard` and
`3.1.0-standard-amd64` (no `v` prefix); `latest` and `latest-<variant>` move
on every release.

```bash
docker tag my-app:build registry.example.com/my-app:1.0.0
```

#### Multi-Region Deployment

**AWS:**
```bash
# Replicate ECR across regions
aws ecr put-replication-configuration \
  --replication-configuration '{"rules":[{"destinations":[{"region":"us-west-2","registryId":"123456789012"}]}]}'
```

**GCP:** create an Artifact Registry repository in a multi-region location
(for example `--location=us`).

## Troubleshooting

### Common Issues

#### Container exits immediately

You are probably running the bare Kimigayo image, whose default command is
`/bin/sh`. Without a TTY the shell exits at once. Deploy an image with your
application as the command (see [What you deploy](#what-you-deploy)).

#### Image Pull Errors

**Solution:**
```bash
# Verify credentials
aws ecr get-login-password | docker login --username AWS --password-stdin <registry-url>

# Check the task execution role has the ECR permissions shown above
```

#### Container Crashes

**Solution:**
```bash
# Check logs
aws logs tail /ecs/my-app

# If your binary fails with "not found", the shared libraries it needs are
# probably missing from the image. Collect them with ldd
# (see examples/python/Dockerfile).
```

#### Network Issues

**Solution:**
- Check security groups allow outbound traffic
- Verify NAT gateway configured for private subnets
- Check DNS resolution

## Support

- [AWS Documentation](https://docs.aws.amazon.com/)
- [Azure Documentation](https://learn.microsoft.com/azure/)
- [GCP Documentation](https://cloud.google.com/docs)
- [Kimigayo OS Issues](https://github.com/Kazuki-0731/Kimigayo/issues)

## Additional Resources

- [AWS ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [GCP Cloud Run Best Practices](https://cloud.google.com/run/docs/best-practices)

---

**Last Updated:** 2026-10-12
**Maintained by:** Kimigayo OS maintainer
