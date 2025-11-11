from unittest.mock import patch, Mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class WeatherDashboardTests(TestCase):
    """Tests for the weather dashboard view."""

    def setUp(self):
        """Create a test user for authentication."""
        self.user = User.objects.create_user(username="testuser", password="testpass123")

    def test_weather_dashboard_requires_login(self):
        """Test that weather dashboard requires authentication."""
        response = self.client.get(reverse("creditos:weather_dashboard"))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertIn("/accounts/login/", response.url)

    @patch("creditos.views.requests.get")
    def test_weather_dashboard_displays_temperature(self, mock_get):
        """Test that weather dashboard displays temperature from API."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "current_weather": {
                "temperature": 22.5,
                "windspeed": 10.5,
                "time": "2024-01-01T12:00",
                "weathercode": 0
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Login and access the weather dashboard
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("creditos:weather_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "creditos/weather_dashboard.html")
        self.assertEqual(response.context["temperature"], 22.5)
        self.assertEqual(response.context["windspeed"], 10.5)

    @patch("creditos.views.requests.get")
    def test_weather_dashboard_handles_api_error(self, mock_get):
        """Test that weather dashboard handles API errors gracefully."""
        # Mock API error using requests.exceptions.RequestException
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("API error")

        # Login and access the weather dashboard
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("creditos:weather_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context.get("error"))
