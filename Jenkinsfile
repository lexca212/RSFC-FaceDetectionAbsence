pipeline {
    agent any

    stages {

        stage('Checkout Code') {
            steps {
                git branch: 'main',
                    credentialsId: 'devops1',
                    url: 'https://github.com/lexca212/RSFC-FaceDetectionAbsence.git'
            }
        }

        stage('Deploy to STAGING') {
            steps {
                sshagent(['ssh-vps']) {
            sh '''
            ssh -o StrictHostKeyChecking=no henoch@192.168.88.21 "
                cd /home/henoch/RSFC_FaceDetectionAbsence || exit
                git pull origin main
                sudo systemctl daemon-reload
                sudo systemctl restart absencedjango.service
            "
            '''
                }
            }
        }

        stage('Approval to Production') {
            steps {
                input message: 'Deploy ke PRODUCTION?', ok: 'Deploy'
            }
        }

        stage('Deploy to PRODUCTION') {
            steps {
                sshagent(['ssh-vps']) {
                    sh """
                    ssh -o StrictHostKeyChecking=no henoch@192.168.88.20 '
                        cd /home/henoch/RSFC_FaceDetectionAbsence || exit
                        git pull origin main
                        sudo systemctl daemon-reload
                        sudo systemctl restart absencedjango.service
                    '
                    """
                }
            }
        }
    }
}
