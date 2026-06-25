# Configuration

## Google Cloud Credentials & ADC Setup

### Prerequisites

1. Install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) (`gcloud`)
2. Have a Google Cloud project with the **Cloud Speech-to-Text API** enabled

### Steps

**1. Log in to Google Cloud**

```bash
gcloud auth login
```

This opens a browser window to authenticate your Google account.

**2. Set your project**

```bash
gcloud config set project YOUR_PROJECT_ID
```

Replace `YOUR_PROJECT_ID` with your project (this project uses `premium-apex-438701-g0`).

**3. Configure Application Default Credentials (ADC)**

```bash
gcloud auth application-default login
```

This opens another browser window. After completing the OAuth flow, credentials are saved to:

```
~/.config/gcloud/application_default_credentials.json
```

These credentials are automatically picked up by the Google Cloud client libraries (including `google-cloud-speech`) via ADC — no additional configuration needed in the code.

**4. Set the quota project**

The ADC setup above automatically adds the quota project for billing. If you need to set it manually:

```bash
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

### Verify

Run the following to confirm ADC is working:

```bash
gcloud auth application-default print-access-token
```

If it prints a token, you're ready to run the scripts.

### Environment Variables

The `.env` file sets the project ID used by Google client libraries:

```
GOOGLE_CLOUD_PROJECT=premium-apex-438701-g0
```

This is loaded automatically when running the server scripts. For `microphone_transcribe.py`, ADC alone is sufficient.
