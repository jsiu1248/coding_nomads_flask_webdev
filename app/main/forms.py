from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo, ValidationError
from ..models import User, Role, ReleaseType


class NameForm(FlaskForm):
    name = StringField("What's your name?", validators=[DataRequired()])
    submit = SubmitField("Submit")


class EditProfileForm(FlaskForm):
    name = StringField("Name", validators=[Length(0, 64)])
    location = StringField("Location", validators=[Length(0,64)])
    bio = TextAreaField("Bio")
    submit = SubmitField("Submit")


class EditProfileAdminForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Length(1,64), Email()])
    username = StringField("Username", validators=[
        DataRequired(), Length(1, 64),
        Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                   'Usernames must have only letters, numbers, dots, or underscores',
        )])
    confirmed = BooleanField("Confirmed")
    role = SelectField("Role", coerce=int)
    name = StringField("Name", validators=[Length(0, 64)])
    location = StringField("Location", validators=[Length(0,64)])
    bio = TextAreaField("Bio")
    submit = SubmitField("Submit")

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # must be given as list of tuples
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError("Email already registered.")

    def validate_username(self, field):
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError("Username already in use.")


class CompositionForm(FlaskForm):
    """What the form DATA is"""
    release_type = SelectField("Release Type", coerce=int, default=ReleaseType.SINGLE, validators=[DataRequired()])
    title = StringField("Title")
    description = TextAreaField("Tell us about your composition")
    submit = SubmitField("Submit")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.release_type.choices = [(ReleaseType.SINGLE, 'Single'),
                                     (ReleaseType.EXTENDED_PLAY, 'EP'),
                                     (ReleaseType.ALBUM, 'Album')]


class CommentForm(FlaskForm):
    body = StringField('', validators=[DataRequired()])
    submit = SubmitField('Submit')