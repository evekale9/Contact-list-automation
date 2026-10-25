# Import libraries
import os
from urllib.parse import urlparse
from uuid import uuid4

import pytest # Run automated tests
from playwright.sync_api import Page, expect
# Website URL
BASE_URL = os.getenv("BASE_URL", "https://thinking-tester-contact-list.herokuapp.com").rstrip("/")
expect.set_options(timeout=10_000)


def is_response(response, path, method):
    return urlparse(response.url).path == path and response.request.method == method

#create a new test user before each test and clean up after
@pytest.fixture
def signed_in_page(page: Page):
    
    page.set_default_timeout(15_000)
    page.set_default_navigation_timeout(30_000)
    try:
        # Open the website
        page.goto(BASE_URL)
        # Open the form
        page.get_by_role("button", name="Sign up", exact=True).click()
        page.wait_for_url("**/addUser", wait_until="load")

        # Fill the new user details
        page.get_by_placeholder("First Name", exact=True).fill("QA")
        page.get_by_placeholder("Last Name", exact=True).fill("Tester")

        # Generate a unique email address
        page.get_by_placeholder("Email", exact=True).fill(f"qa-{uuid4().hex}@example.com")

        #Gen a unique password
        page.get_by_placeholder("Password", exact=True).fill(f"Qa!{uuid4().hex}")

        # Wait for the server response
        with page.expect_response(lambda r: is_response(r, "/users", "POST")) as response:
            page.get_by_role("button", name="Submit", exact=True).click()
        # Check the Succesfull registration 
        assert response.value.status == 201, "User registration should succeed"
        page.wait_for_url("**/contactList", wait_until="load")
        yield page
    finally:
        
        token = next((c["value"] for c in page.context.cookies() if c["name"] == "token"), None)
        if token:
            headers = {"Authorization": f"Bearer {token}"}
            response = page.request.get(f"{BASE_URL}/contacts", headers=headers)
            assert response.ok, "Cleanup could not list the test user's contacts"
            for item in response.json():
                deleted = page.request.delete(f"{BASE_URL}/contacts/{item['_id']}", headers=headers)
                assert deleted.ok, "Cleanup could not delete a test contact"
            deleted = page.request.delete(f"{BASE_URL}/users/me", headers=headers)
            assert deleted.ok, "Cleanup could not delete the test user"


@pytest.fixture
def contact():
    """Fresh synthetic data for every test."""
    return {
        "firstName": "Eva", "lastName": "Tester", "birthdate": "1998-06-31",
        "email": f"contact-{uuid4().hex}@example.com", "phone": "2101234567",
        "street1": "Dimitriou 18", "street2": "Apartment 2", "city": "Athens",
        "stateProvince": "Attica", "postalCode": "18121", "country": "Greece",
    }

# Open the contact form and fill in all contact details
def fill_contact(page: Page, data):
    page.get_by_role("button", name="Add a New Contact", exact=True).click()
    # Wait for the form's script to load before submitting it.
    page.wait_for_url("**/addContact", wait_until="load")
    for field, value in data.items():
        page.locator(f"#{field}").fill(value)


def submit_contact(page: Page):
    with page.expect_response(lambda r: is_response(r, "/contacts", "POST")) as response:
        page.get_by_role("button", name="Submit", exact=True).click()
    return response.value


def contact_row(page: Page, email):
    return page.locator("tr").filter(has=page.get_by_text(email, exact=True))


def open_contact(page: Page, email):
    contact_row(page, email).click()
    page.wait_for_url("**/contactDetails", wait_until="load")


def load_list(page: Page, action):
    """An absence check must wait until the list has actually loaded."""
    with page.expect_response(lambda r: is_response(r, "/contacts", "GET")) as response:
        action()
    assert response.value.status == 200
    expect(page.locator(".contactTable")).to_be_visible()

# First requirement: Register a user, add a contact, and validate the details
def test_register_add_and_validate_contact(signed_in_page: Page, contact):
    page = signed_in_page
    fill_contact(page, contact)
    assert submit_contact(page).status == 201
    page.wait_for_url("**/contactList", wait_until="load")
    expect(contact_row(page, contact["email"])).to_have_count(1)
    open_contact(page, contact["email"])
    for field, value in contact.items():
        expect(page.locator(f"#{field}")).to_have_text(value)
    page.reload()
    expect(page.locator("#email")).to_have_text(contact["email"])

# Check that an invalid birthdate is rejected
def test_invalid_birthdate(signed_in_page: Page, contact):
    page = signed_in_page
    invalid_contact = {**contact, "birthdate": "not-a-date"}
    fill_contact(page, invalid_contact)
    assert submit_contact(page).status == 400
    expect(page).to_have_url(f"{BASE_URL}/addContact")
    expect(page.locator("#error")).to_be_visible()
    expect(page.locator("#error")).to_contain_text("Birthdate is invalid")
    load_list(page, lambda: page.get_by_role("button", name="Cancel", exact=True).click())
    expect(contact_row(page, contact["email"])).to_have_count(0)

# Delete an existing contact.
def test_delete_contact(signed_in_page: Page, contact):
    page = signed_in_page
    fill_contact(page, contact)
    assert submit_contact(page).status == 201
    page.wait_for_url("**/contactList", wait_until="load")
    expect(contact_row(page, contact["email"])).to_have_count(1)
    open_contact(page, contact["email"])
    def accept_deletion(dialog):
        assert dialog.type == "confirm"
        assert dialog.message == "Are you sure you want to delete this contact?"
        dialog.accept()

    page.once("dialog", accept_deletion)
    with page.expect_response(lambda r: r.request.method == "DELETE" and urlparse(r.url).path.startswith("/contacts/")) as deletion:
        load_list(page, lambda: page.get_by_role("button", name="Delete Contact", exact=True).click())
    assert deletion.value.ok
    expect(contact_row(page, contact["email"])).to_have_count(0)
    load_list(page, lambda: page.reload())
    expect(contact_row(page, contact["email"])).to_have_count(0)

