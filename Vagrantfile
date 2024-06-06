Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"

  config.ssh.insert_key = false
  config.ssh.forward_agent = true
  config.vm.hostname = "globus-django-portal"

  config.vm.network "private_network", ip: "192.168.1.183"
  config.vm.network "forwarded_port", guest: 8000, host: 48000, id: 'django-dev'

  config.vm.provision :ansible do |ansible|
    ansible.playbook = "ansible/playbook.yml"
    ansible.compatibility_mode = "2.0"
    ansible.groups = {
      "globus-portal-dev-vagrant" => ["default"]
    }
  end

  config.vm.provider "virtualbox" do |v|
    v.name = "globus-portal-dev.local"
    v.memory = 6144
    v.customize ["modifyvm", :id, "--natdnshostresolver1", "on", "--audio", "none"]
  end
end
