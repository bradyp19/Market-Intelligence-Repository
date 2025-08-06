# Cloud Deployment Strategy for Competitive Intelligence System

## AWS Deployment (Recommended)

### Infrastructure Components

1. **Compute**: ECS Fargate or EKS for containerized deployment
2. **Database**: Amazon RDS for PostgreSQL (Multi-AZ for production)
3. **Container Registry**: Amazon ECR
4. **Load Balancer**: Application Load Balancer (ALB)
5. **DNS**: Route 53
6. **SSL**: AWS Certificate Manager
7. **Monitoring**: CloudWatch + X-Ray
8. **Secrets**: AWS Secrets Manager
9. **Backup**: RDS automated backups + point-in-time recovery

### Deployment Steps

#### 1. Infrastructure Setup (Terraform/CloudFormation)
```hcl
# terraform/main.tf
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "competitive-intel-vpc"
  }
}

resource "aws_db_subnet_group" "main" {
  name       = "competitive-intel-db-subnet-group"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  
  tags = {
    Name = "competitive-intel-db-subnet-group"
  }
}

resource "aws_db_instance" "postgres" {
  identifier     = "competitive-intel-db"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.medium"
  
  allocated_storage     = 100
  max_allocated_storage = 1000
  storage_type         = "gp3"
  storage_encrypted    = true
  
  db_name  = "competitive_intelligence"
  username = "postgres"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = false
  final_snapshot_identifier = "competitive-intel-final-snapshot"
  
  tags = {
    Name = "competitive-intel-db"
  }
}

resource "aws_ecs_cluster" "main" {
  name = "competitive-intel-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}
```

#### 2. CI/CD Pipeline (GitHub Actions)
```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS

on:
  push:
    branches: [main, production]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v2
    
    - name: Build and push Docker image
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: competitive-intel-app
        IMAGE_TAG: ${{ github.sha }}
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
        echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT
    
    - name: Deploy to ECS
      env:
        IMAGE_URI: ${{ steps.build-image.outputs.image }}
      run: |
        # Update ECS service with new image
        aws ecs update-service \
          --cluster competitive-intel-cluster \
          --service competitive-intel-service \
          --force-new-deployment
```

#### 3. ECS Task Definition
```json
{
  "family": "competitive-intel-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "app",
      "image": "ACCOUNT.dkr.ecr.REGION.amazonaws.com/competitive-intel-app:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "FLASK_ENV",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "DB_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT:secret:competitive-intel/db-password"
        },
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT:secret:competitive-intel/secret-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/competitive-intel-app",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

## Alternative: Google Cloud Platform (GCP)

### Infrastructure Components
1. **Compute**: Google Kubernetes Engine (GKE) or Cloud Run
2. **Database**: Cloud SQL for PostgreSQL
3. **Container Registry**: Artifact Registry
4. **Load Balancer**: Cloud Load Balancing
5. **DNS**: Cloud DNS
6. **SSL**: Google-managed SSL certificates
7. **Monitoring**: Cloud Monitoring + Cloud Trace
8. **Secrets**: Secret Manager

### GKE Deployment
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: competitive-intel-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: competitive-intel-app
  template:
    metadata:
      labels:
        app: competitive-intel-app
    spec:
      containers:
      - name: app
        image: gcr.io/PROJECT_ID/competitive-intel-app:latest
        ports:
        - containerPort: 8000
        env:
        - name: DB_HOST
          value: "127.0.0.1"
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: password
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
      - name: cloudsql-proxy
        image: gcr.io/cloudsql-docker/gce-proxy:latest
        command:
          - "/cloud_sql_proxy"
          - "-instances=PROJECT_ID:REGION:INSTANCE_NAME=tcp:5432"
        securityContext:
          runAsNonRoot: true
```

## Alternative: Microsoft Azure

### Infrastructure Components
1. **Compute**: Azure Container Instances or Azure Kubernetes Service
2. **Database**: Azure Database for PostgreSQL
3. **Container Registry**: Azure Container Registry
4. **Load Balancer**: Azure Application Gateway
5. **DNS**: Azure DNS
6. **SSL**: Azure Key Vault certificates
7. **Monitoring**: Azure Monitor + Application Insights
8. **Secrets**: Azure Key Vault

### Cost Optimization Recommendations

1. **Database**: Start with smaller instances, enable auto-scaling
2. **Compute**: Use spot instances for non-critical workloads
3. **Storage**: Use appropriate storage tiers (Standard vs Premium)
4. **CDN**: Implement CloudFront/CDN for static assets
5. **Reserved Instances**: Purchase reserved capacity for predictable workloads

### Security Best Practices

1. **Network**: Private subnets, security groups, WAF
2. **IAM**: Least privilege access, service accounts
3. **Encryption**: At-rest and in-transit encryption
4. **Secrets**: Never hardcode secrets, use managed secret services
5. **Monitoring**: Enable comprehensive logging and alerting
6. **Updates**: Regular security updates and vulnerability scanning
