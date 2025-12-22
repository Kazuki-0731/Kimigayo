# Kimigayo OS - Cloud Deployment Guide

This guide explains how to deploy Kimigayo OS on major cloud platforms.

## Table of Contents

- [AWS (Amazon Web Services)](#aws)
- [Azure (Microsoft Azure)](#azure)
- [GCP (Google Cloud Platform)](#gcp)
- [General Best Practices](#best-practices)

---

## AWS (Amazon Web Services) {#aws}

### Container Deployment

#### Amazon ECS (Elastic Container Service)

**1. Push image to ECR**

```bash
# Authenticate to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.us-east-1.amazonaws.com

# Tag image
docker tag ishinokazuki/kimigayo-os:latest \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/kimigayo-os:latest

# Push image
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/kimigayo-os:latest
```

**2. Create ECS Task Definition**

```json
{
  "family": "kimigayo-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "kimigayo-container",
      "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/kimigayo-os:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {
          "name": "NODE_ENV",
          "value": "production"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/kimigayo",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "wget --spider localhost:8080/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

**3. Deploy with AWS CLI**

```bash
# Create service
aws ecs create-service \
  --cluster kimigayo-cluster \
  --service-name kimigayo-service \
  --task-definition kimigayo-app:1 \
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
  name: kimigayo-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: kimigayo
  template:
    metadata:
      labels:
        app: kimigayo
    spec:
      containers:
      - name: kimigayo
        image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/kimigayo-os:latest
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
  name: kimigayo-service
spec:
  type: LoadBalancer
  selector:
    app: kimigayo
  ports:
  - port: 80
    targetPort: 8080
```

### EC2 Deployment (Advanced)

For EC2 deployment, you would need to create a custom AMI. This is more complex and requires:

1. Build rootfs tarball
2. Create custom AMI using EC2 Image Builder
3. Configure instance with user data

**Note**: EC2 deployment is recommended only for advanced users. Container-based deployment (ECS/EKS) is preferred.

---

## Azure (Microsoft Azure) {#azure}

### Container Deployment

#### Azure Container Instances (ACI)

**1. Push image to ACR**

```bash
# Login to ACR
az acr login --name myregistry

# Tag image
docker tag ishinokazuki/kimigayo-os:latest \
  myregistry.azurecr.io/kimigayo-os:latest

# Push image
docker push myregistry.azurecr.io/kimigayo-os:latest
```

**2. Deploy to ACI**

```bash
az container create \
  --resource-group myResourceGroup \
  --name kimigayo-container \
  --image myregistry.azurecr.io/kimigayo-os:latest \
  --cpu 1 \
  --memory 1 \
  --registry-login-server myregistry.azurecr.io \
  --registry-username <username> \
  --registry-password <password> \
  --dns-name-label kimigayo-app \
  --ports 80
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
      "name": "kimigayo-group",
      "location": "[resourceGroup().location]",
      "properties": {
        "containers": [
          {
            "name": "kimigayo-container",
            "properties": {
              "image": "myregistry.azurecr.io/kimigayo-os:latest",
              "resources": {
                "requests": {
                  "cpu": 1,
                  "memoryInGb": 1
                }
              },
              "ports": [
                {
                  "port": 80,
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
              "port": 80
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
  --name kimigayo-cluster \
  --node-count 3 \
  --node-vm-size Standard_B2s \
  --generate-ssh-keys

# Get credentials
az aks get-credentials \
  --resource-group myResourceGroup \
  --name kimigayo-cluster

# Deploy (same Kubernetes manifests as EKS)
kubectl apply -f deployment.yaml
```

---

## GCP (Google Cloud Platform) {#gcp}

### Container Deployment

#### Cloud Run

**1. Push image to GCR**

```bash
# Configure Docker for GCR
gcloud auth configure-docker

# Tag image
docker tag ishinokazuki/kimigayo-os:latest \
  gcr.io/my-project/kimigayo-os:latest

# Push image
docker push gcr.io/my-project/kimigayo-os:latest
```

**2. Deploy to Cloud Run**

```bash
gcloud run deploy kimigayo-service \
  --image gcr.io/my-project/kimigayo-os:latest \
  --platform managed \
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
  name: kimigayo-service
spec:
  template:
    spec:
      containers:
      - image: gcr.io/my-project/kimigayo-os:latest
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
gcloud container clusters create kimigayo-cluster \
  --num-nodes 3 \
  --machine-type e2-small \
  --region us-central1

# Get credentials
gcloud container clusters get-credentials kimigayo-cluster \
  --region us-central1

# Deploy (same Kubernetes manifests)
kubectl apply -f deployment.yaml
```

---

## Best Practices {#best-practices}

### Security

#### 1. Use Private Container Registries

```bash
# AWS ECR
aws ecr create-repository --repository-name kimigayo-os

# Azure ACR
az acr create --resource-group myRG --name myregistry --sku Basic

# GCP GCR
# Automatically available with project
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
      "Resource": "arn:aws:ecr:*:*:repository/kimigayo-os"
    }
  ]
}
```

#### 3. Enable Container Scanning

**AWS:**
```bash
aws ecr put-image-scanning-configuration \
  --repository-name kimigayo-os \
  --image-scanning-configuration scanOnPush=true
```

**Azure:**
```bash
az acr task create \
  --name scan-on-push \
  --registry myregistry \
  --context /dev/null \
  --cmd mcr.microsoft.com/azure-defender/scan:latest
```

**GCP:**
```bash
gcloud container images scan gcr.io/my-project/kimigayo-os:latest
```

### Cost Optimization

#### 1. Right-Size Resources

**Kimigayo OS recommended sizes:**

| Workload Type | CPU | Memory | Notes |
|---------------|-----|--------|-------|
| Minimal (static) | 0.25 vCPU | 256 MB | Static websites |
| Standard (API) | 0.5-1 vCPU | 512 MB | RESTful APIs |
| Heavy (processing) | 1-2 vCPU | 1-2 GB | Data processing |

#### 2. Use Spot/Preemptible Instances

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

**GKE Preemptible Nodes:**
```bash
gcloud container node-pools create preemptible-pool \
  --cluster kimigayo-cluster \
  --preemptible \
  --num-nodes 3
```

#### 3. Auto-scaling

**AWS ECS:**
```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/kimigayo-cluster/kimigayo-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 1 \
  --max-capacity 10
```

**GCP Cloud Run (automatic):**
```bash
gcloud run services update kimigayo-service \
  --min-instances 0 \
  --max-instances 10
```

### Monitoring

#### AWS CloudWatch

```bash
# View logs
aws logs tail /ecs/kimigayo --follow

# Create alarm
aws cloudwatch put-metric-alarm \
  --alarm-name kimigayo-high-cpu \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80
```

#### Azure Monitor

```bash
# View logs
az monitor log-analytics query \
  --workspace <workspace-id> \
  --analytics-query "ContainerLog | where Name == 'kimigayo-container'"
```

#### GCP Cloud Monitoring

```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=kimigayo-service"
```

### Backup and Disaster Recovery

#### Image Versioning

Always tag images with semantic versioning:

```bash
docker tag image:latest registry/image:v1.2.3
docker tag image:latest registry/image:v1.2
docker tag image:latest registry/image:v1
docker tag image:latest registry/image:latest
```

#### Multi-Region Deployment

**AWS:**
```bash
# Replicate ECR across regions
aws ecr put-replication-configuration \
  --replication-configuration '{"rules":[{"destinations":[{"region":"us-west-2","registryId":"123456789012"}]}]}'
```

**GCP:**
```bash
# Use multi-regional GCR
docker push gcr.io/my-project/kimigayo-os:latest
# Automatically replicated
```

## Cost Estimates

### Monthly Cost Comparison (3 containers, 24/7)

| Platform | Service | Config | Est. Cost |
|----------|---------|--------|-----------|
| **AWS** | ECS Fargate | 0.25 vCPU, 0.5GB | ~$15-20/month |
| **Azure** | ACI | 1 vCPU, 1GB | ~$30-35/month |
| **GCP** | Cloud Run | 1 vCPU, 512MB | ~$10-15/month* |

\* Cloud Run pricing based on request count and execution time

### Optimization Tips

1. **Use managed container services** (ECS Fargate, Cloud Run) for small workloads
2. **Use Kubernetes** (EKS, AKS, GKE) for large-scale deployments
3. **Enable auto-scaling** to match demand
4. **Use spot instances** for non-critical workloads
5. **Leverage Kimigayo OS's small size** to reduce data transfer costs

## Troubleshooting

### Common Issues

#### Image Pull Errors

**Solution:**
```bash
# Verify credentials
aws ecr get-login-password | docker login --username AWS --password-stdin <registry-url>

# Check IAM permissions
aws iam get-role-policy --role-name ecsTaskExecutionRole --policy-name ECSTaskExecutionPolicy
```

#### Container Crashes

**Solution:**
```bash
# Check logs
aws logs tail /ecs/kimigayo

# Increase memory if needed
# Update task definition with more memory
```

#### Network Issues

**Solution:**
- Check security groups allow outbound traffic
- Verify NAT gateway configured for private subnets
- Check DNS resolution

## Support

- [AWS Documentation](https://docs.aws.amazon.com/)
- [Azure Documentation](https://docs.microsoft.com/azure/)
- [GCP Documentation](https://cloud.google.com/docs)
- [Kimigayo OS Issues](https://github.com/Kazuki-0731/Kimigayo/issues)

## Additional Resources

- [AWS ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [Azure Container Best Practices](https://docs.microsoft.com/azure/container-instances/container-instances-best-practices)
- [GCP Cloud Run Best Practices](https://cloud.google.com/run/docs/best-practices)

---

**Last Updated:** 2025-12-22
**Maintained by:** Kimigayo OS Team
