[![Build Status](https://travis-ci.org/etcaterva/eas-backend.svg?branch=master)](https://travis-ci.org/etcaterva/eas-backend)
[![Coverage Status](https://coveralls.io/repos/github/etcaterva/eas-backend/badge.svg?branch=master)](https://coveralls.io/github/etcaterva/eas-backend?branch=master)

EAS Backend services

## Working locally
#### Set up local environment

```bash
python3.6 -m venv .venv
source .venv/bin/activate
pip install -r requirements/local.txt

./manage.py makemigrations
```

#### Validate Changes

```bash
coverage run manage.py test
coverage report

pylint eas
```

#### Run a local version

```bash
./manage.py migrate
./manage.py runserver
```

Check `/api/swagger` or `/api/redoc`.

Swagger file available in `/api/swagger.yaml` or by running
```bash
./manage.py generate_swagger
```

#### Run dev version

```bash
docker-componse build
docker-compose run web python manage.py makemigrrations
docker-compose run web python manage.py migrate
docker-compose up
```
