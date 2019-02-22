# Installation

## Linux Installation

These instructions have been tested on Debian Jessie.

### Increase `vm.max_map_count`

Increase `vm.max_map_count` to at least 262144, to make elasticsearch happy - see [the official documentation][] for details.
[the official documentation]: https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html#docker-cli-run-prod-mode

### Install docker

```shell
apt-get install -y apt-transport-https ca-certificates curl gnupg2 software-properties-common python3.6 python3-pip
pip3 install -r requirements.txt
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
apt-get update
apt-get install -y docker-ce
service docker start
curl -L https://github.com/docker/compose/releases/download/1.22.0/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

### Clone the repo and set up folders

```shell
git clone https://github.com/hoover/docker-setup /opt/hoover
cd /opt/hoover
mkdir -p volumes volumes/metrics volumes/metrics/users volumes/search-es-snapshots volumes/search-es/data collections
chmod 777 volumes/search-es-snapshots volumes/search-es/data
```

### Spin up

Spin up the docker containers, run migrations, create amdin user

```shell
docker-compose run --rm search ./manage.py migrate
docker-compose run --rm search ./manage.py createsuperuser
docker-compose run --rm ui npm run build
docker-compose run --rm search ./manage.py collectstatic --noinput
docker-compose up -d
```

### Import the test dataset

```shell
git clone https://github.com/hoover/testdata collections/testdata
./createcollection -c testdata
```

### Adding custom settings for docker services
To add custom settings to docker services create a file `docker-custom-services.yml` in the
`templates` directory and add services with custom settings there in yml format. E.g.:
```yaml
  search-es:
    environment:
      ES_JAVA_OPTS: -Xms2g -Xmx2g
```

After that run the update script:
```shell
./updatesettings
```

## OS specific notes

### Installation on Windows 10 using Docker for Windows

All in all the above instructions are applicable, however there are a few things to consider 
when using Windows10 for this setup.
First, go to the Docker for Windows settings and increases the amount of 
memory that it will access. (I've set it to 8GB). Otherwise Elastic will 
exit with out of memory errors. (The default value is 2GB)


* Make sure that line endings are not changed 

When checking out on git, it may change the line endings of files, which may cause 
problems with a few scripts.
`git config --global core.autocrlf input`
will keep the line endings the way they are in the repository. You should also change
the default line endings in your default text editor if possible.
	

* Permissions of the created folders in step 3
	
First of all, Windows Powershell will not create multiple folders by using mkdir -p.
You can use for example the Git Bash to avoid creating all folders by hand.
Secondly, you have to set the necessary folder permissions by hand.
Right-click on the folder -> properties -> security -> edit -> add   then
add the user 'everybody' and give it full access to the folders. This is the 
equivalent of using CHMOD 777 on a Linux maching.
I also gave full access to the group 'docker-user' but I'm not sure if it is strictly necessary.
	
*	Creating volumes for postgres databases

All postgres databases need	a volume that is created by hand in Docker for Windows 
use `docker volume create --name=postgres_volume_name -d local` to create the volume

Then, edit docker-compose.yml (here, the name of the created volume is search-pg-DB) add 
	
```bash
search-pg-DB:
    external: true
```

to the volumes section

and replace `- ./volumes/search-pg/data:/var/lib/postgresql/data` in the volumes part of the service search-pg 
with ` - search-pg-DB:/var/lib/postgresql/data`

when you create a new postgres database for the testdata, you have to create another volume and make similar
changes to  docker-compose.override.yml . Here, you have to create the volumes section:

```bash
volumes:
your_second_volume_name:
    external: true
```

And update the volume part of the service snoop-pg--testdata accordingly
`your_second_volume_name:/var/lib/postgresql/data`
