![Build Status](https://github.com/etcaterva/eas-backend/actions/workflows/test-and-deploy.yml/badge.svg?branch=master)
[![Coverage Status](https://coveralls.io/repos/github/etcaterva/eas-backend/badge.svg?branch=master)](https://coveralls.io/github/etcaterva/eas-backend?branch=master)

EAS Backend services

## Working locally

#### Set up local environment

```bash
python3.8 -m venv .venv
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

The following env vars enable additional services:

- `EAS_AWS_KEY_SECRET`: Send emails (Get from AWS portal).
- `EAS_LAMADAVA_APIK`: Instagram (Get from hikerapi console).
- `EAS_LAMATOK_APIK`: TikTok (Get from lamatok console).
- `EAS_PAYPAL_SECRET`: Sandbox KEY for paypal payments.
- `EAS_REVOLUT_SECRET`: Sandbox KEY for revolut payments.

All keys are in lastpass.

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
