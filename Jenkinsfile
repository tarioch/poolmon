def label = 'build-deploy-app'
def packerVersion = '1.2.3'

podTemplate(label: label, idleMinutes: 15, containers: [
  containerTemplate(name: 'docker', image: 'docker', command: 'cat', ttyEnabled: true),
  containerTemplate(name: 'helm', image: 'lachlanevenson/k8s-helm', command: 'cat', ttyEnabled: true)
],
volumes: [
  hostPathVolume(mountPath: '/var/run/docker.sock', hostPath: '/var/run/docker.sock')
]) {
  node(label) {
    stage('Create Docker images') {
      container('docker') {
        checkout scm: scm
        sh "rm -f packer_${packerVersion}_linux_amd64.zip"
        sh "wget https://releases.hashicorp.com/packer/${packerVersion}/packer_${packerVersion}_linux_amd64.zip"
        
        sh "rm -f /bin/packer"
        sh "unzip packer_${packerVersion}_linux_amd64.zip -d /bin"

        sh "packer version"
        sh "packer build -color=false template.json"
        sh "docker images"
      }
    }
  }
}
