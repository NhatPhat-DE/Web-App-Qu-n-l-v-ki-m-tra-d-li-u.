import getpass
import sys
import warnings
from app.services.accounts import bootstrap_admin, AccountError


def main():
    if len(sys.argv) != 1:
        print('Lệnh này không nhận tham số; hãy nhập thông tin trong lời nhắc.')
        return 1
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            username = getpass.getpass('Tên đăng nhập: ')
            password = getpass.getpass('Mật khẩu: ')
            confirmation = getpass.getpass('Xác nhận mật khẩu: ')
        if password != confirmation:
            raise AccountError('Xác nhận mật khẩu không khớp.')
        identifier = bootstrap_admin(username, password)
        print(f'Đã tạo admin đầu tiên, ID {identifier}. API nghiệp vụ vẫn chưa được bảo vệ.')
        return 0
    except (EOFError, KeyboardInterrupt):
        print('Đã hủy; chưa hoàn tất tạo admin.')
        return 1
    except AccountError as error:
        print(str(error))
        return 1
    except Exception:
        print('Không thể tạo admin an toàn. Dùng terminal tương tác hỗ trợ nhập ẩn và kiểm tra cấu hình database.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
