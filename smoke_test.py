"""
Django Smoke Test Script
Runs test client requests against all main URLs.
Returns non-zero exit code on any failure.
"""
import os
import sys
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from django.test import Client


def run_smoke_tests():
    client = Client()
    results = []
    all_passed = True

    # URLs to test with GET
    get_urls = [
        ('/', 'Homepage'),
        ('/projects/', 'Project List'),
        ('/about/', 'About'),
        ('/resume/', 'Resume'),
        ('/education/', 'Education'),
        ('/certifications/', 'Certifications'),
        ('/contact/', 'Contact GET'),
    ]

    for url, name in get_urls:
        try:
            response = client.get(url)
            if response.status_code == 200:
                results.append((name, url, 'PASS', response.status_code))
            else:
                results.append((name, url, 'FAIL', f'Status {response.status_code}'))
                all_passed = False
        except Exception as e:
            results.append((name, url, 'FAIL', str(e)))
            print(f'\n{"="*60}')
            print(f'EXCEPTION on {name} ({url}):')
            print("="*60)
            traceback.print_exc()
            print("="*60 + '\n')
            all_passed = False

    # Test POST to /contact/ with valid data
    try:
        post_data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Smoke Test',
            'message': 'This is a smoke test message.',
        }
        response = client.post('/contact/', post_data)
        # Should redirect (302) on success or return 200 with form
        if response.status_code in [200, 302]:
            results.append(('Contact POST', '/contact/', 'PASS', response.status_code))
        else:
            results.append(('Contact POST', '/contact/', 'FAIL', f'Status {response.status_code}'))
            all_passed = False
    except Exception as e:
        results.append(('Contact POST', '/contact/', 'FAIL', str(e)))
        print(f'\n{"="*60}')
        print(f'EXCEPTION on Contact POST (/contact/):')
        print("="*60)
        traceback.print_exc()
        print("="*60 + '\n')
        all_passed = False

    # Print results table
    print('\n' + '='*60)
    print('SMOKE TEST RESULTS')
    print('='*60)
    print(f'{"Test":<20} {"URL":<15} {"Result":<8} {"Details"}')
    print('-'*60)
    for name, url, result, details in results:
        print(f'{name:<20} {url:<15} {result:<8} {details}')
    print('='*60)

    if all_passed:
        print('\nALL TESTS PASSED')
        return 0
    else:
        print('\nSOME TESTS FAILED')
        return 1


if __name__ == '__main__':
    sys.exit(run_smoke_tests())
