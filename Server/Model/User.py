from Server.Model.Base import Base


class Register(Base):
    Login: str
    Password: str
    Username: str


class Login(Base):
    Login: str | None = None
    Password: str | None = None
    AccessToken: str | None = None


class User(Base):
    Password: str | None = None
    Login: str | None = None
    # or
    AccessToken: str | None = None



class AccessToken(Base):
    Token: str


class RefreshToken(Base):
    Token: str


class LoginResponse(Base):
    AccessToken: str
    RefreshToken: str


class UserAuth(Base):
    Username: str
    Id: int
