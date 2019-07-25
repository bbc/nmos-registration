Vagrant.configure("2") do |config|
    puts "Configuring proxy settings..."
  if Vagrant.has_plugin?("vagrant-proxyconf")
    puts "Found vagrant-proxyconf plugin - Now checking envinronent variables..."
    if ENV["http_proxy"]
      puts "http_proxy is set to: " + ENV["http_proxy"]
      config.proxy.http     = ENV["http_proxy"]
      config.apt_proxy.http = ENV["http_proxy"]
    end
    if ENV["https_proxy"]
      puts "https_proxy is set to: " + ENV["https_proxy"]
      config.proxy.https    = ENV["https_proxy"]
      config.apt_proxy.https = ENV["https_proxy"]
    end
    if ENV["no_proxy"]
      puts "no_proxy paths set to: " + ENV["no_proxy"]
      config.proxy.no_proxy = ENV["no_proxy"] + ",172.28.0.1/16"
    end
  end

  config.vm.define "registration" do |registration|
    registration.vm.hostname = "registration"
    registration.vm.box = "bento/ubuntu-16.04"
    registration.vm.provider "virtualbox" do |vb|
        vb.gui = false
        vb.linked_clone = true
        vb.memory = 4096
        vb.customize ["modifyvm", :id, "--uartmode1", "disconnected" ]
        vb.customize ["storagectl", :id, "--name", "SATA Controller", "--hostiocache", "on" ]
      end
    registration.vm.network "private_network", type: "dhcp"
    registration.vm.network "forwarded_port", guest: 80, host: 8080
    registration.vm.network "forwarded_port", guest: 8091, host: 1908
    registration.vm.synced_folder "../", "/vagrant-root"
    registration.vm.boot_timeout = 600
  end

  # Provision each VM
  config.vm.provision :ansible do |ansible|
    ansible.playbook = "provisioning/install_playbook.yml"
  end
end