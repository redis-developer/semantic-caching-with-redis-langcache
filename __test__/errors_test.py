from app.errors import ClientError


def test_client_error_is_an_exception():
    err = ClientError(400, "Bad Request")

    assert isinstance(err, Exception)
    assert isinstance(err, ClientError)


def test_client_error_preserves_status_and_message():
    err = ClientError(404, "Not Found")

    assert err.status == 404
    assert str(err) == "Not Found"
