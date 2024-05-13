
#Class для проверки функций и методов в классах на ошибки:
class ErrorHandledClass:
    def __init__(self):
        pass

    def log_error(self, error_message, function_name):
        with open("error_logs_from_users.txt", "a") as file:
            file.write(f"Error in function '{function_name}': {error_message}\n")



# Функция-декоратор для перехвата и логирования исключений:
def error_handler_decorator(obj):
    if isinstance(obj, type):  # Check if obj is a class
        for attr_name in obj.__dict__:
            if callable(getattr(obj, attr_name)):
                setattr(obj, attr_name, error_handler_decorator(getattr(obj, attr_name)))
        return obj
    elif callable(obj):  # Check if obj is a callable object (function or method)
        def wrapper(*args, **kwargs):
            try:
                return obj(*args, **kwargs)
            except Exception as e:
                function_name = obj.__name__ if hasattr(obj, '__name__') else type(obj).__name__
                error_message = str(e)
                error_handler.log_error(error_message, function_name)
                print("Error logged successfully:", error_message)
        return wrapper
    else:
        raise TypeError("Error handler decorator can only be applied to classes or callable objects")

# Создание экземпляра класса ErrorHandler
error_handler = ErrorHandledClass()