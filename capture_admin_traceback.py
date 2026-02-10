import os
import traceback

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client


def main() -> int:
    client = Client(HTTP_HOST="127.0.0.1")

    # Use a dedicated automation admin so we don't depend on your real password.
    User = get_user_model()
    username = os.environ.get("DJANGO_ADMIN_USERNAME", "claude_admin")
    email = os.environ.get("DJANGO_ADMIN_EMAIL", "steven@originami.com")
    password = os.environ.get("DJANGO_ADMIN_PASSWORD", "TempPass_ChangeMe123!")

    user, _ = User.objects.get_or_create(username=username, defaults={"email": email})
    user.is_staff = True
    user.is_superuser = True
    user.set_password(password)
    user.save()

    logged_in = client.login(username=username, password=password)

    url = "/admin/portfolio/sitesetting/"
    try:
        response = client.get(url, follow=True)

        tb = []
        tb.append(f"logged_in={logged_in}")
        tb.append(f"initial_status={response.redirect_chain[0][1] if response.redirect_chain else response.status_code}")
        tb.append(f"final_status={response.status_code}")
        tb.append(f"redirect_chain={response.redirect_chain}")

        exc = getattr(response, "exc_info", None)
        if exc:
            tb.append("\\nEXCEPTION:\\n" + "".join(traceback.format_exception(*exc)))
        else:
            # If no exception, still include the final URL and a short body hint
            try:
                content_snip = response.content.decode("utf-8", errors="replace")[:800]
            except Exception:
                content_snip = "<could not decode response content>"
            tb.append("\\nCONTENT_SNIFF:\\n" + content_snip)

        report_path = os.path.join(os.getcwd(), "CLAUDE_BUGREPORT.md")
        with open(report_path, "a", encoding="utf-8") as f:
            f.write("\\n\\n---\\n\\n## Auto-captured traceback (authenticated, follow redirects)\\n\\n`	ext\\n")
            f.write("\\n".join(tb))
            f.write("\\n`\\n")

        print(f"Wrote diagnostic block to: {report_path}")
        return 0

    except Exception:
        report_path = os.path.join(os.getcwd(), "CLAUDE_BUGREPORT.md")
        with open(report_path, "a", encoding="utf-8") as f:
            f.write("\\n\\n---\\n\\n## Auto-captured traceback (script exception)\\n\\n`	ext\\n")
            f.write(traceback.format_exc())
            f.write("\\n`\\n")
        print(f"Wrote exception to: {report_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
