## Getting Things Running

To get started with development with python 3.7 or higher:

```bash
python3 -m venv env
source env/bin/activate
pip install -r requirements/dev.txt
source development.sh
```

Then start a `flask shell` session and enter the following:

```bash
flask shell
```
```python
>>> db.create_all()
>>> Role.insert_roles()
>>> exit()
```

If you want the app to send emails, including confirmation emails, you must have an email that accepts SMTP authentication. Should you have such an email set up correctly, you must then set the environment variables `MAIL_USERNAME`, `MAIL_PASSWORD`, and `RAGTIME_ADMIN`. Below is an example bash script you can `source` to enable email-sending capabilities:

```bash
# MAIL_PASSWORD depends on your email provider
# put the below in a file (ex: email.sh)
export MAIL_USERNAME=yourusername
export MAIL_PASSWORD=<password or app password>
export RAGTIME_ADMIN=yourusername@example.com
```
```bash
source email.sh
```

If you want to bypass the confirmation email in order to access the site, enter another `flask shell` session and type:

```bash
flask shell
```
```python
>>> u = User.query.filter_by(username='<your username>').first()
>>> u.confirmed = True
>>> db.session.commit()
>>> quit()
```

To generate fake data, do this:
```bash
flask shell
```
```python
# use however many users or compositions you want to generate
>>> from app import fake
>>> fake.users(count=20)
>>> fake.compositions(count=200)
```

## Cool features

You can tag other users in your track descriptions using `@`. It will create a link to their page.

> Had a totally fun time in this collab with @eyoung!

## Known bugs
- The dropdown for Release Type in the home page must be change before you can submit the form, or it complains about you not selecting a value.
- Yes, I know it looks ugly. :) Styling coming soon.


Have fun. c: