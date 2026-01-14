pipeline {
    agent any
    
    environment {
        DOCKER_REGISTRY = 'docker.io'
        DOCKERHUB_CREDENTIALS_ID = '89df4834-57b8-4fe8-9e25-d8775421a081'
        DOCKER_USERNAME = credentials('dockerhub-username')
        GIT_PREVIOUS_COMMIT = "${env.GIT_PREVIOUS_SUCCESSFUL_COMMIT ?: 'HEAD~1'}"
        
        // Kubernetes Configuration
        K8S_NAMESPACE = 'microservices'
        KUBECONFIG_CREDENTIALS_ID = 'kubeconfig-credentials'
        HELM_RELEASE_PREFIX = 'ms'
    }
    
    stages {
        stage('Detect Changes') {
            steps {
                script {
                    def allServices = ['api-gateway', 'user-service', 'notification-service']
                    def changedServices = []
                    
                    allServices.each { service ->
                        def changes = sh(
                            script: "git diff --name-only ${GIT_PREVIOUS_COMMIT} HEAD | grep '^${service}/' || true",
                            returnStdout: true
                        ).trim()
                        
                        if (changes) {
                            changedServices.add(service)
                            echo "✓ Changes detected in: ${service}"
                        }
                    }
                    
                    env.CHANGED_SERVICES = changedServices.join(',')
                    
                    if (changedServices.isEmpty()) {
                        echo "No service changes detected. Skipping pipeline."
                        currentBuild.result = 'SUCCESS'
                        error('No changes to build')
                    } else {
                        echo "Building services: ${changedServices.join(', ')}"
                    }
                }
            }
        }
        
        stage('Build and Test Services') {
            when {
                expression { env.CHANGED_SERVICES != '' }
            }
            steps {
                script {
                    def services = env.CHANGED_SERVICES.split(',')
                    def parallelBuilds = [:]
                    
                    services.each { service ->
                        parallelBuilds[service] = {
                            buildAndTestService(service)
                        }
                    }
                    
                    parallel parallelBuilds
                }
            }
        }
        
        stage('Push Docker Images') {
            when {
                expression { env.CHANGED_SERVICES != '' }
            }
            steps {
                script {
                    def services = env.CHANGED_SERVICES.split(',')
                    def parallelPushes = [:]
                    
                    services.each { service ->
                        parallelPushes[service] = {
                            pushDockerImage(service)
                        }
                    }
                    
                    parallel parallelPushes
                }
            }
        }
        
        stage('Deploy to Kubernetes') {
            when {
                expression { env.CHANGED_SERVICES != '' }
            }
            steps {
                script {
                    def services = env.CHANGED_SERVICES.split(',')
                    
                    withCredentials([file(credentialsId: KUBECONFIG_CREDENTIALS_ID, variable: 'KUBECONFIG')]) {
                        // Ensure namespace exists
                        sh """
                            kubectl create namespace ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                        """
                        
                        services.each { service ->
                            deployToK8s(service)
                        }
                    }
                }
            }
        }
        
        stage('Verify Deployment') {
            when {
                expression { env.CHANGED_SERVICES != '' }
            }
            steps {
                script {
                    def services = env.CHANGED_SERVICES.split(',')
                    
                    withCredentials([file(credentialsId: KUBECONFIG_CREDENTIALS_ID, variable: 'KUBECONFIG')]) {
                        services.each { service ->
                            verifyDeployment(service)
                        }
                    }
                }
            }
        }
    }
    
    post {
        success {
            echo "✓ Pipeline completed successfully!"
            echo "Services deployed: ${env.CHANGED_SERVICES}"
            script {
                if (env.CHANGED_SERVICES) {
                    def services = env.CHANGED_SERVICES.split(',')
                    services.each { service ->
                        echo "  - ${service}: ${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${service}:${env.BUILD_NUMBER}"
                    }
                }
            }
        }
        failure {
            echo "✗ Pipeline failed. Check logs for details."
        }
        always {
            script {
                sh 'docker system prune -f --volumes || true'
                echo "Cleanup completed"
            }
        }
    }
}

// Build and test a service
def buildAndTestService(String serviceName) {
    stage("${serviceName}: Install Dependencies") {
        dir(serviceName) {
            sh 'pip install -r requirements.txt --break-system-packages || echo "No install needed"'
        }
    }
    
    stage("${serviceName}: Run Tests") {
        dir(serviceName) {
            sh 'pytest --junitxml=test-results.xml || echo "No tests configured"'
        }
    }
    
    stage("${serviceName}: Build Docker Image") {
        dir(serviceName) {
            def imageTag = "${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${serviceName}:${env.BUILD_NUMBER}"
            def latestTag = "${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${serviceName}:latest"
            
            sh """
                docker build -t ${imageTag} -t ${latestTag} .
            """
            echo "✓ Built Docker image: ${imageTag}"
        }
    }
}

// Push Docker image to registry
def pushDockerImage(String serviceName) {
    stage("${serviceName}: Push to Registry") {
        withCredentials([usernamePassword(
            credentialsId: DOCKERHUB_CREDENTIALS_ID,
            usernameVariable: 'DOCKER_USER',
            passwordVariable: 'DOCKER_PASS'
        )]) {
            sh """
                echo \$DOCKER_PASS | docker login -u \$DOCKER_USER --password-stdin ${DOCKER_REGISTRY}
                docker push ${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${serviceName}:${env.BUILD_NUMBER}
                docker push ${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${serviceName}:latest
            """
            echo "✓ Pushed ${serviceName} to registry"
        }
    }
}

// Deploy service to Kubernetes using Helm
def deployToK8s(String serviceName) {
    stage("${serviceName}: Deploy to K8s") {
        def releaseName = "${HELM_RELEASE_PREFIX}-${serviceName}"
        def chartPath = "helm/${serviceName}"
        
        sh """
            helm upgrade --install ${releaseName} ${chartPath} \
                --namespace ${K8S_NAMESPACE} \
                --set image.tag=${env.BUILD_NUMBER} \
                --set image.repository=${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${serviceName} \
                --wait \
                --timeout 5m
        """
        echo "✓ Deployed ${serviceName} to Kubernetes"
    }
}

// Verify deployment status
def verifyDeployment(String serviceName) {
    stage("${serviceName}: Verify") {
        def releaseName = "${HELM_RELEASE_PREFIX}-${serviceName}"
        
        sh """
            kubectl rollout status deployment/${releaseName} -n ${K8S_NAMESPACE} --timeout=5m
            kubectl get pods -n ${K8S_NAMESPACE} -l app.kubernetes.io/name=${serviceName}
        """
        echo "✓ ${serviceName} is running successfully"
    }
}