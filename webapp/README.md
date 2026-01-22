# Web App

A thin frontend client that consumes the compliance API.

## Purpose

This web app is a **consumer** of the API, not a source of business logic. All compliance logic lives in the backend pipeline.

## Features

- **Image Upload**: Upload images via drag-and-drop or file picker
- **API Integration**: Calls the `/analyze` endpoint with image and domain
- **Evidence Visualization**: Displays violations, risk scores, and evidence in a clear UI

## Architecture

```
User → Web App → API → Pipeline → Models → Outcome
```

The web app:
1. Accepts image uploads
2. Sends multipart/form-data to `/analyze`
3. Receives JSON outcome
4. Renders violations and evidence visually

## No Business Logic

- No rule checking in the frontend
- No model inference in the frontend
- No compliance calculations
- Just presentation and API calls

## Usage

1. Start the API: `python app.py`
2. Open `index.html` in a browser
3. Upload an image and select domain
4. View compliance results

## Future Enhancements

- Image preview with violation overlays
- Evidence highlighting on image
- Batch upload support
- Export results as PDF/JSON
