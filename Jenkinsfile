@Library("rd-apmm-groovy-ci-library@v1.x") _

/*
 Runs the following steps in parallel and reports results to GitHub:
 - Lint using flake8
 - Run Python 3 unit tests in tox
 - Build Debian packages for supported Ubuntu versions

 If these steps succeed and the master branch is being built, wheels and debs are uploaded to PyPI and the
 R&D Debian mirrors.

 Optionally you can set FORCE_PYUPLOAD to force upload to PyPI, and FORCE_DEBUPLOAD to force Debian package
 upload on non-master branches.
*/

pipeline {
    agent {
        label "ubuntu&&apmm-slave"
    }
    options {
        ansiColor('xterm') // Add support for coloured output
        buildDiscarder(logRotator(numToKeepStr: '10')) // Discard old builds
    }
    parameters {
        booleanParam(name: "FORCE_PYUPLOAD", defaultValue: false, description: "Force Python artifact upload")
        booleanParam(name: "FORCE_DEBUPLOAD", defaultValue: false, description: "Force Debian package upload")
        booleanParam(name: "DESTROY_VAGRANT", defaultValue: true, description: "Destroy Vagrant box before build?")
    }
    triggers {
        upstream (upstreamProjects: "apmm-repos/nmos-common/master")
    }
    environment {
        http_proxy = "http://www-cache.rd.bbc.co.uk:8080"
        https_proxy = "http://www-cache.rd.bbc.co.uk:8080"
    }
    stages {
        stage("Clean Environment") {
            when {
                expression { return params.DESTROY_VAGRANT }
            }
            steps {
                sh 'vagrant destroy -f'
            }
        }
        stage("Setup Environment") {
            steps {
                sh 'git clean -dfx -e .vagrant'
                withBBCGithubSSHAgent {
                    bbcVagrantUp(update: true)
                }
            }
        }
        stage("Finalise Vagrant Setup") {
            steps{
                sh 'vagrant ssh -c "sudo gpasswd -a vagrant docker"'
                sh 'vagrant halt && vagrant up' // Should investigate further, but a restart is required for docker to pull image
                sh 'vagrant ssh -c "cd /vagrant && make clean"'
            }
        }
        stage ("Tests") {
            parallel {
                stage ("Py3 Linting Check") {
                    steps {
                        script {
                            env.lint3_result = "FAILURE"
                        }
                        bbcGithubNotify(context: "lint/flake8_3", status: "PENDING")
                        // Run the linter
                        sh 'python3 -m flake8'
                        script {
                            env.lint3_result = "SUCCESS" // This will only run if the sh above succeeded
                        }
                    }
                    post {
                        always {
                            bbcGithubNotify(context: "lint/flake8_3", status: env.lint3_result)
                        }
                    }
                }
                stage ("Tests") {
                    stages {
                        stage ("Python 3 Unit & Integration Tests") {
                            steps {
                                script {
                                    env.py3_result = "FAILURE"
                                }
                                bbcGithubNotify(context: "tests/py3", status: "PENDING")
                                sh 'vagrant ssh -c "cd /vagrant && make test"'
                                script {
                                    env.py3_result = "SUCCESS" // This will only run if the sh above succeeded
                                }
                            }
                            post {
                                always {
                                    bbcGithubNotify(context: "tests/py3", status: env.py3_result)
                                }
                            }
                        }
                    }
                }
            }
        }
        stage ("Debian Source Build") {
            steps {
                script {
                    env.debSourceBuild_result = "FAILURE"
                }
                bbcGithubNotify(context: "deb/sourceBuild", status: "PENDING")

                sh 'python3 ./setup.py sdist'
                sh 'make dsc'
                bbcPrepareDsc()
                stash(name: "deb_dist", includes: "deb_dist/*")
                script {
                    env.debSourceBuild_result = "SUCCESS" // This will only run if the steps above succeeded
                }
            }
            post {
                always {
                    bbcGithubNotify(context: "deb/sourceBuild", status: env.debSourceBuild_result)
                }
            }
        }
        stage ("Build Packages") {
            parallel{
                stage ("Build Deb with pbuilder") {
                    steps {
                        script {
                            env.pbuilder_result = "FAILURE"
                        }
                        bbcGithubNotify(context: "deb/packageBuild", status: "PENDING")
                        // Build for all supported platforms and extract results into workspace
                        bbcParallelPbuild(
                            stashname: "deb_dist",
                            dists: bbcGetSupportedUbuntuVersions(),
                            arch: "amd64")
                        script {
                            env.pbuilder_result = "SUCCESS" // This will only run if the steps above succeeded
                        }
                    }
                    post {
                        success {
                            archiveArtifacts artifacts: "_result/**"
                        }
                        always {
                            bbcGithubNotify(context: "deb/packageBuild", status: env.pbuilder_result)
                        }
                    }
                }
            }
        }
        stage ("Upload Packages") {
            // Duplicates the when clause of each upload so blue ocean can nicely display when stage skipped
            when {
                anyOf {
                    expression { return params.FORCE_PYUPLOAD }
                    expression { return params.FORCE_DEBUPLOAD }
                    expression {
                        bbcShouldUploadArtifacts(branches: ["master"])
                    }
                }
            }
            parallel {
                stage ("Upload to PyPI") {
                    when {
                        anyOf {
                            expression { return params.FORCE_PYUPLOAD }
                            expression {
                                bbcShouldUploadArtifacts(branches: ["master"])
                            }
                        }
                    }
                    steps {
                        script {
                            env.pypiUpload_result = "FAILURE"
                        }
                        bbcGithubNotify(context: "pypi/upload", status: "PENDING")
                        sh 'rm -rf dist/*'
                        bbcMakeGlobalWheel("py27")
                        bbcMakeGlobalWheel("py3")
                        bbcTwineUpload(toxenv: "py3", pypi: true)
                        script {
                            env.pypiUpload_result = "SUCCESS" // This will only run if the steps above succeeded
                        }
                    }
                    post {
                        always {
                            bbcGithubNotify(context: "pypi/upload", status: env.pypiUpload_result)
                        }
                    }
                }
                stage ("upload deb") {
                    when {
                        anyOf {
                            expression { return params.FORCE_DEBUPLOAD }
                            expression {
                                bbcShouldUploadArtifacts(branches: ["master"])
                            }
                        }
                    }
                    steps {
                        script {
                            env.debUpload_result = "FAILURE"
                        }
                        bbcGithubNotify(context: "deb/upload", status: "PENDING")
                        script {
                            for (def dist in bbcGetSupportedUbuntuVersions()) {
                                bbcDebUpload(sourceFiles: "_result/${dist}-amd64/*",
                                             removePrefix: "_result/${dist}-amd64",
                                             dist: "${dist}",
                                             apt_repo: "ap/python")
                            }
                        }
                        script {
                            env.debUpload_result = "SUCCESS" // This will only run if the steps above succeeded
                        }
                    }
                    post {
                        always {
                            bbcGithubNotify(context: "deb/upload", status: env.debUpload_result)
                        }
                    }
                }
            }
        }
    }
    post {
        always {
            bbcSlackNotify()
        }
    }
}
