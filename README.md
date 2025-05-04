# Happy Robot Technical Challenge

A FastAPI-based service that processes and routes call data with analytics capabilities.

## Overview

This service provides two main functionalities:
1. **Call Processing API**: Receives and processes call data, evaluates whether calls should be made, and forwards them to a workflow system.
2. **Analytics Dashboard**: Tracks and visualizes call metrics and performance data.

## Features

- **Call Deduplication**: Prevents duplicate calls from being processed
- **Carrier Validation**: Verifies carrier MC numbers through FMCSA
- **Call Analytics**: Tracks call outcomes, durations, and rates
- **Real-time Dashboard**: Visualizes call metrics and performance data
- **API Key Authentication**: Secures all endpoints

## API Endpoints

### Call Processing
- `POST /process-load`: Processes new load calls with deduplication
- `POST /process-call`: Logs call analytics data

### Analytics
- `GET /metrics`: Returns call metrics in JSON format
- `GET /dashboard`: Serves the analytics dashboard UI (open access, no authentication required)

## Environment Variables

Required environment variables:
- `API_KEY`: For API authentication
- `WF2_URL`: Workflow 2 endpoint URL
- `FMC_WEB_KEY`: For FMCSA authentication
- `WF2_API_KEY`: Workflow 2 API key

## Deployment

The service is deployed on Render.com at:
```
https://happyrobot-technical-challenge.onrender.com
```

The dashboard can be accessed directly without authentication at:
```
https://happyrobot-technical-challenge.onrender.com/dashboard
```

To open the dashboard on macOS, run:
```bash
open https://happyrobot-technical-challenge.onrender.com/dashboard
```

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export API_KEY=your_api_key
export WF2_URL=your_workflow_url
export WF2_API_KEY=your_workflow_key
export FMC_WEB_KEY=your_fmcsa_key
```

3. Run the server:
```bash
uvicorn app.main:app --reload
```

## Technologies Used

- FastAPI
- Pydantic
- Pandas
- Jinja2
- Uvicorn
- Render.com

