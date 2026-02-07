# BigEye Pro - Backend Setup Guide

## Overview
This backend system uses Google Apps Script + Google Sheets + Google Drive to create a serverless backend for:
- License verification & HWID auto-binding
- Encrypted prompt/dictionary storage (updateable without rebuilding .exe)
- Usage monitoring (anti-abuse)
- Automated accounting (auto-log transactions when expiry date changes)

---

## Step 1: Create Google Sheet Database

1. Go to [Google Sheets](https://sheets.google.com) and create a new spreadsheet
2. Name it: `BigEye_Database`
3. Copy the **Spreadsheet ID** from the URL:
   ```
   https://docs.google.com/spreadsheets/d/[THIS_IS_YOUR_SPREADSHEET_ID]/edit
   ```

### Sheet Structure

#### Sheet 1: `Configuration`
| Key | Value |
|-----|-------|
| Prompt_ID_iStock | (Google Doc ID for iStock prompt) |
| Prompt_ID_Hybrid | (Google Doc ID for Hybrid prompt) |
| Prompt_ID_Single | (Google Doc ID for Single Words prompt) |
| Dict_File_ID | (Text file ID for keyword dictionary) |

#### Sheet 2: `Licenses`
| Column | Field | Description |
|--------|-------|-------------|
| A | License_Key | Primary Key (e.g., TLE-001) |
| B | First_Name | Customer first name |
| C | Last_Name | Customer last name |
| D | Contact_Info | Email / Line ID |
| E | Hardware_ID | Auto-bound HWID |
| F | Expiry_Date | Format: YYYY-MM-DD |
| G | Status | 'Active' or 'Banned' |
| H | Last_Login | Timestamp |
| I | Total_Photos | Accumulated photo count |
| J | Total_Videos | Accumulated video count |
| K | Days_Left | Auto-calculated |

#### Sheet 3: `Transactions`
| Column | Field |
|--------|-------|
| A | Timestamp |
| B | License_Key |
| C | Name |
| D | Type (New/Renew) |
| E | Amount |
| F | Tax_Month |

---

## Step 2: Create Prompt Files (Google Docs)

1. Create 3 new Google Docs:
   - `prompt_istock` - Contains iStock prompt template
   - `prompt_hybrid` - Contains Hybrid mode prompt template
   - `prompt_single` - Contains Single Words prompt template

2. Copy prompts from `config.py` into each doc (use placeholders like `{keyword_count}`, `{title_limit}`, etc.)

3. Get each Doc's ID from the URL:
   ```
   https://docs.google.com/document/d/[THIS_IS_THE_DOC_ID]/edit
   ```

4. Create a plain text file for the Dictionary:
   - Upload `keywords_db.txt` to Google Drive
   - Get the File ID from the URL

5. Update the `Configuration` sheet with these IDs

---

## Step 3: Deploy Google Apps Script

1. Go to [Google Apps Script](https://script.google.com)
2. Create a new project: `BigEye_Backend`
3. Replace all code in `Code.gs` with the content from `backend/code.gs`
4. **Important:** Update `SPREADSHEET_ID` at line 17:
   ```javascript
   const SPREADSHEET_ID = 'YOUR_ACTUAL_SPREADSHEET_ID';
   ```

5. Run `initializeSpreadsheet()` once to set up the database structure

6. Deploy as Web App:
   - Click **Deploy** > **New deployment**
   - Select type: **Web app**
   - Description: `BigEye Backend v2.0`
   - Execute as: **Me**
   - Who has access: **Anyone**
   - Click **Deploy**
   - Copy the **Web App URL** (you'll need this for the Python client)

---

## Step 4: Set Up Automated Accounting Trigger

1. In Apps Script editor, go to **Triggers** (clock icon)
2. Click **+ Add Trigger**
3. Configure:
   - Function: `onEdit`
   - Event source: **From spreadsheet**
   - Event type: **On edit**
4. Click **Save**

Now when you change any Expiry_Date in the Licenses sheet, a transaction will be automatically logged!

---

## Step 5: Update Python Client

Update the `LICENSE_API_URL` in `license/validator_api.py`:
```python
LICENSE_API_URL = 'https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec'
```

---

## API Endpoints

| Action | Parameters | Description |
|--------|------------|-------------|
| `verify` | key, uuid | Verify license |
| `activate` | key, uuid, name, email, line_id | Activate & bind HWID |
| `fetch_config` | key, uuid | Get encrypted prompts/dict |
| `update_usage` | key, photos, videos | Report usage stats |
| `log_transaction` | key, name, type, amount, tax_month | Manual transaction log |
| `ping` | - | Health check |

### Example Request:
```
GET https://script.google.com/.../exec?action=verify&key=TLE-001&uuid=abc123
```

---

## Security Notes

1. **Encryption:** All prompts and dictionary are encrypted before transmission using XOR cipher + Base64
2. **HWID Binding:** License is locked to first device that activates it
3. **Server-side validation:** All checks happen on Google's servers
4. **No local storage:** Sensitive data (prompts) never saved to disk on client

---

## Troubleshooting

### "License not found"
- Check that the License_Key exists in the Licenses sheet

### "Device mismatch"
- License is bound to another device
- Admin must clear Hardware_ID column to allow re-binding

### "Permission denied" when fetching config
- Check that Google Doc/Drive files are accessible
- Ensure Apps Script has permission to access Drive

### Transactions not auto-logging
- Verify the onEdit trigger is installed
- Check that you're editing Column F (Expiry_Date) specifically
