[![Build Status](https://travis-ci.org/etcaterva/eas-backend.svg?branch=master)](https://travis-ci.org/etcaterva/eas-backend)
[![Coverage Status](https://coveralls.io/repos/github/etcaterva/eas-backend/badge.svg?branch=master)](https://coveralls.io/github/etcaterva/eas-backend?branch=master)

EAS Backend services

## Working locally
#### Set up local environment

```bash
sudo apt-get install rabbitmq-server
python3.6 -m venv .venv
source .venv/bin/activate
pip install -r requirements/local.txt

./manage.py makemigrations
```

#### Validate Changes

```bash
make lint
make test
```

#### Run a local version

```bash
make runlocal
```

Optionally, run the following to get emails working:

```bash
docker run -d -p 5672:5672 rabbitmq
EAS_MAIL_PASSWORD="<set password>" celery --app celery-task worker
```

#### Working on the swagger file

```bash
docker pull swaggerapi/swagger-editor
docker run -d -p 8080:8080 swaggerapi/swagger-editor
```

#### Run dev version

```bash
docker-componse build
docker-compose run web python manage.py makemigrrations
docker-compose run web python manage.py migrate
docker-compose up
```
