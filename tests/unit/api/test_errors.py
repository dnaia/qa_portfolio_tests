from fastapi import HTTPException


def test_error_inheritance(error_instance):
    """Каждая ошибка должна быть наследником HTTPException."""
    assert isinstance(error_instance, HTTPException)


def test_error_has_correct_status_and_detail(error_instance, error_class):
    """Проверяем, что дефолтные status_code и detail совпадают с определёнными в классе."""
    assert error_instance.status_code == error_class.status_code
    assert error_instance.detail == error_class.detail


def test_error_example(error_instance):
    """Проверяем, что example возвращает правильный ResponseMsg."""
    example = error_instance.example
    assert example == {"detail": error_instance.detail}


def test_error_response_schema(error_instance):
    """Проверяем, что response_schema корректен и содержит нужные поля."""
    schema = error_instance.response_schema

    assert error_instance.status_code in schema

    entry = schema[error_instance.status_code]

    assert entry["description"] == error_instance.__doc__
    assert entry["content"]["application/json"]["example"] == {"detail": error_instance.detail}
