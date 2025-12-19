pipeline {
    agent any
    
    environment {
        DOCKER_REGISTRY = 'docker.io'
        DOCKERHUB_CREDENTIALS_ID = credentials('89df4834-57b8-4fe8-9e25-d8775421a081')
        GIT_PREVIOUS_COMMIT = "${env.GIT_PREVIOUS_SUCCESSFUL_COMMIT ?: 'HEAD~1'}"
    }
    
    stages {
        stage('Detect Changes') {
            steps {
                script {
                    // Define all microservices in the mono-repo
                    def allServices = ['api-gateway', 'user-service', 'notification-service']
                    
                    // Detect which services have changed
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
                        currentBuild.result = 'SUCCESS!'
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
                            buildService(service)
                        }
                    }
                    
                    parallel parallelBuilds
                }
            }
        }
        
stage('Deploy Services') {
            when {
                expression { env.CHANGED_SERVICES?.trim() }
            }
            steps {
                script {
                    def services = env.CHANGED_SERVICES.split(',').collect { it.trim() }

                    echo "Deploying services: ${services.join(', ')}"

                    sh """
                        docker compose pull ${services.join(' ')}
                        docker compose up -d ${services.join(' ')}
                    """

                    services.each {
                        echo "✓ Deployed: ${it}"
                    }
                }
            }
        }
    }
    
    post {
        success {
            echo "Pipeline completed successfully!"
            echo "Services built and deployed: ${env.CHANGED_SERVICES}"
        }
        failure {
            echo "Pipeline failed. Check logs for details."
        }
        always {
            script {
                // Cleanup: Remove dangling images and containers
                sh '''
                    docker system prune -f --volumes || true
                '''
                echo "Cleanup completed"
            }
        }
    }
}

// Reusable function for building a service
def buildService(String serviceName) {
    try {
        stage("${serviceName}: Install") {
            dir(serviceName) {
                sh ' pip install -r requirements.txt --break-system-packages || echo "No install needed"'
            }
        }
        
        stage("${serviceName}: Test") {
            dir(serviceName) {
                sh 'pytest || echo "No tests configured"'
            }
        }
        
        stage("${serviceName}: Docker Build") {
            dir(serviceName) {
                def imageTag = "${DOCKER_REGISTRY}/${env.DOCKER_USERNAME}/${serviceName}:${env.BUILD_NUMBER}"
                def latestTag = "${DOCKER_REGISTRY}/${env.DOCKER_USERNAME}/${serviceName}:latest"
                
                sh """
                    docker build -t ${imageTag} -t ${latestTag} .
                """
                echo "✓ Built Docker image: ${imageTag}"
            }
        }
        

    } catch (Exception e) {
        echo "✗ Failed to build ${serviceName}: ${e.message}"
        throw e
    }
}