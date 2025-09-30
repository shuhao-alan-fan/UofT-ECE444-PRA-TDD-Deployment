import os
import pytest
import json
from pathlib import Path
from flask import session
from project.app import app, db, login_required

TEST_DB = "test.db"

# This is a pytest fixture, which sets up a known state for each test function before the test runs.
@pytest.fixture
def client():
    BASE_DIR = Path(__file__).resolve().parent.parent
    app.config["TESTING"] = True
    app.config["DATABASE"] = BASE_DIR.joinpath(TEST_DB)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{BASE_DIR.joinpath(TEST_DB)}"

    with app.app_context():
        db.create_all()  # setup
        yield app.test_client()  # tests run here
        db.drop_all()  # teardown


def login(client, username, password):
    """Login helper function"""
    return client.post(
        "/login",
        data=dict(username=username, password=password),
        follow_redirects=True,
    )


def logout(client):
    """Logout helper function"""
    return client.get("/logout", follow_redirects=True)


def test_index(client):
    response = client.get("/", content_type="html/text")
    assert response.status_code == 200


def test_database(client):
    """initial test. ensure that the database exists"""
    tester = Path("test.db").is_file()
    assert tester


def test_empty_db(client):
    """Ensure database is blank"""
    rv = client.get("/")
    assert b"No entries yet. Add some!" in rv.data


def test_login_logout(client):
    """Test login and logout using helper functions"""
    rv = login(client, app.config["USERNAME"], app.config["PASSWORD"])
    assert b"You were logged in" in rv.data
    rv = logout(client)
    assert b"You were logged out" in rv.data
    rv = login(client, app.config["USERNAME"] + "x", app.config["PASSWORD"])
    assert b"Invalid username" in rv.data
    rv = login(client, app.config["USERNAME"], app.config["PASSWORD"] + "x")
    assert b"Invalid password" in rv.data


def test_messages(client):
    """Ensure that user can post messages"""
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    rv = client.post(
        "/add",
        data=dict(title="<Hello>", text="<strong>HTML</strong> allowed here"),
        follow_redirects=True,
    )
    assert b"No entries here so far" not in rv.data
    assert b"&lt;Hello&gt;" in rv.data
    assert b"<strong>HTML</strong> allowed here" in rv.data

def test_delete_message(client):
    """Ensure the messages are being deleted"""
    rv = client.get("/delete/1")
    data = json.loads(rv.data)
    assert data["status"] == 0
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    rv = client.get("/delete/1")
    data = json.loads(rv.data)
    assert data["status"] == 1


# def test_search(client):
#     rv = client.get('/search/',content_type = "html/text")
#     assert b"First" in rv.data
#     assert b"query" in rv.data

def test_search(client):
    # First log in and add a post through the /add route
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    client.post(
        "/add",
        data=dict(title="First", text="Hello World"),
        follow_redirects=True,
    )

    # Now search for it
    rv = client.get("/search/?query=First")
    assert rv.status_code == 200
    assert b"First" in rv.data   # title shows up
    assert b"Hello World" in rv.data  # body shows up


def test_login(client):
    rv = client.get('/delete/1')
    data = json.loads(rv.data)
    assert data["status"] != 1


def dummy_view():
    return "OK", 200

@login_required
def protected_view():
    return dummy_view()

def test_login_required_not_logged_in(client):
    """Blocks access when not logged in"""
    with app.test_request_context():
        session.clear()
        response, status = protected_view()
        assert status == 401
        assert response.json["status"] == 0
        assert response.json["message"] == "Please log in."

def test_login_required_logged_in(client):
    """Allows access when logged in"""
    with app.test_request_context():
        session["logged_in"] = True
        response, status = protected_view()
        assert status == 200
        assert response == "OK"