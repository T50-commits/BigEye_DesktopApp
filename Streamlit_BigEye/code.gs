/**
 * BigEye Pro - Backend System (Google Apps Script)
 * ================================================
 * Serverless backend for license verification, config storage, 
 * usage monitoring, and automated accounting.
 * 
 * SETUP INSTRUCTIONS:
 * 1. Create a new Google Apps Script project
 * 2. Copy this entire code to Code.gs
 * 3. Create a Google Sheet with 3 sheets: 'Configuration', 'Licenses', 'Transactions'
 * 4. Update SPREADSHEET_ID below with your Sheet ID
 * 5. Create Google Docs for prompts and update File IDs in 'Configuration' sheet
 * 6. Deploy as Web App (Execute as: Me, Who has access: Anyone)
 */

// ==========================================
// CONFIGURATION
// ==========================================
// สำหรับ Container-Bound Script (ผูกกับ Sheet) ใช้ getActiveSpreadsheet()
// ถ้าเป็น Standalone Script ให้ใส่ ID ตรงๆ เช่น '1ABC...xyz'
const SPREADSHEET_ID = null; // ใช้ null สำหรับ Container-Bound Script

// Encryption Key (MUST match client-side key)
const ENCRYPTION_KEY = 'BigEye_SecureTransport_2026_!@#$%^&*';

// Sheet Names (ต้องตรงกับชื่อ Sheet ใน Google Sheets)
const SHEET_CONFIG = 'Configuration';
const SHEET_LICENSES = 'Licenses';
const SHEET_TRANSACTIONS = 'Transactions';

// ==========================================
// ENCRYPTION UTILITIES (XOR + Base64)
// ==========================================

/**
 * Generate cipher key from secret string
 */
function getCipherKey() {
  const key = [];
  for (let i = 0; i < ENCRYPTION_KEY.length; i++) {
    key.push(ENCRYPTION_KEY.charCodeAt(i));
  }
  // Extend key using simple hash
  while (key.length < 32) {
    let sum = 0;
    for (let i = 0; i < key.length; i++) {
      sum = (sum + key[i] * (i + 1)) % 256;
    }
    key.push(sum);
  }
  return key;
}

/**
 * Encrypt plain text using XOR cipher + Base64
 */
function encryptData(plainText) {
  if (!plainText) return '';
  
  const key = getCipherKey();
  const signature = 'BIGEYE_ENC_V2:';
  const textBytes = Utilities.newBlob(plainText).getBytes();
  const encryptedBytes = [];
  
  // Add signature bytes
  for (let i = 0; i < signature.length; i++) {
    encryptedBytes.push(signature.charCodeAt(i));
  }
  
  // XOR encryption
  for (let i = 0; i < textBytes.length; i++) {
    encryptedBytes.push(textBytes[i] ^ key[i % key.length]);
  }
  
  return Utilities.base64Encode(encryptedBytes);
}

/**
 * Decrypt encrypted text
 */
function decryptData(encryptedText) {
  if (!encryptedText) return null;
  
  try {
    const key = getCipherKey();
    const signature = 'BIGEYE_ENC_V2:';
    const rawBytes = Utilities.base64Decode(encryptedText);
    
    // Check signature
    let sigMatch = true;
    for (let i = 0; i < signature.length; i++) {
      if (rawBytes[i] !== signature.charCodeAt(i)) {
        sigMatch = false;
        break;
      }
    }
    
    if (!sigMatch) return null;
    
    // XOR decryption
    const decryptedBytes = [];
    for (let i = signature.length; i < rawBytes.length; i++) {
      decryptedBytes.push(rawBytes[i] ^ key[(i - signature.length) % key.length]);
    }
    
    return Utilities.newBlob(decryptedBytes).getDataAsString();
  } catch (e) {
    Logger.log('Decryption error: ' + e);
    return null;
  }
}

// ==========================================
// SPREADSHEET HELPERS
// ==========================================

/**
 * Get spreadsheet instance
 * Supports both Container-Bound and Standalone scripts
 */
function getSpreadsheet() {
  if (SPREADSHEET_ID) {
    return SpreadsheetApp.openById(SPREADSHEET_ID);
  } else {
    // Container-Bound Script - ใช้ getActiveSpreadsheet()
    return SpreadsheetApp.getActiveSpreadsheet();
  }
}

/**
 * Get sheet by name
 */
function getSheet(sheetName) {
  return getSpreadsheet().getSheetByName(sheetName);
}

/**
 * Find row by license key in Licenses sheet
 * Returns: { row: number, data: array } or null
 */
function findLicenseRow(licenseKey) {
  const sheet = getSheet(SHEET_LICENSES);
  const data = sheet.getDataRange().getValues();
  
  for (let i = 1; i < data.length; i++) { // Skip header
    if (data[i][0] === licenseKey) {
      return { row: i + 1, data: data[i] };
    }
  }
  return null;
}

/**
 * Get configuration value by key
 * Searches all rows (including row 1) for the key
 */
function getConfigValue(key) {
  const sheet = getSheet(SHEET_CONFIG);
  const data = sheet.getDataRange().getValues();
  
  // Start from i=0 to include first row (no header assumed)
  for (let i = 0; i < data.length; i++) {
    if (data[i][0] === key) {
      return data[i][1];
    }
  }
  Logger.log('Config key not found: ' + key);
  return null;
}

// ==========================================
// LICENSE MANAGEMENT
// ==========================================

/**
 * Verify License - Main verification function
 * Checks: License Key, HWID, Expiry, Status
 */
function verifyLicense(licenseKey, hwid) {
  try {
    const result = findLicenseRow(licenseKey);
    
    if (!result) {
      return {
        success: false,
        message: 'License key not found',
        require_activation: false
      };
    }
    
    const row = result.row;
    const data = result.data;
    
    // Column mapping (0-indexed):
    // A=0: License_Key, B=1: First_Name, C=2: Last_Name, D=3: Contact_Info
    // E=4: Hardware_ID, F=5: Expiry_Date, G=6: Status, H=7: Last_Login
    // I=8: Total_Photos, J=9: Total_Videos, K=10: Days_Left (calculated)
    
    const storedHwid = data[4];
    const expiryDate = data[5];
    const status = data[6];
    const firstName = data[1];
    const lastName = data[2];
    
    // Check status
    if (status === 'Banned') {
      return {
        success: false,
        message: 'License has been banned. Contact support.',
        require_activation: false
      };
    }
    
    // Check HWID - Auto-binding on first use
    if (!storedHwid || storedHwid === '') {
      return {
        success: false,
        message: 'License not activated on any device',
        require_activation: true
      };
    }
    
    // Check HWID match
    if (storedHwid !== hwid) {
      return {
        success: false,
        message: 'Device mismatch. This license is registered to another device.',
        require_activation: false
      };
    }
    
    // Check expiry
    const today = new Date();
    const expiry = new Date(expiryDate);
    const daysLeft = Math.ceil((expiry - today) / (1000 * 60 * 60 * 24));
    
    if (daysLeft < 0) {
      return {
        success: false,
        message: 'License expired on ' + Utilities.formatDate(expiry, 'Asia/Bangkok', 'dd/MM/yyyy'),
        days_left: 0,
        require_activation: false
      };
    }
    
    // Update Last_Login (Column H = index 8)
    const sheet = getSheet(SHEET_LICENSES);
    const now = Utilities.formatDate(new Date(), 'Asia/Bangkok', 'dd/MM/yyyy HH:mm:ss');
    sheet.getRange(row, 8).setValue(now);
    
    // ไม่เขียน Days_Left - ให้ใช้สูตรใน Sheet: =IF(F3="","",F3-TODAY())
    
    return {
      success: true,
      message: 'License valid',
      name: firstName + ' ' + lastName,
      expire_date: Utilities.formatDate(expiry, 'Asia/Bangkok', 'dd/MM/yyyy'),
      days_left: daysLeft,
      status: status
    };
    
  } catch (e) {
    Logger.log('verifyLicense error: ' + e);
    return {
      success: false,
      message: 'Server error: ' + e.message
    };
  }
}

/**
 * Activate License - Auto-bind HWID on first activation
 */
function activateLicense(licenseKey, hwid, name, email, lineId) {
  try {
    const result = findLicenseRow(licenseKey);
    
    if (!result) {
      return {
        success: false,
        message: 'License key not found'
      };
    }
    
    const row = result.row;
    const data = result.data;
    const storedHwid = data[4];
    const status = data[6];
    
    // Check if banned
    if (status === 'Banned') {
      return {
        success: false,
        message: 'License has been banned'
      };
    }
    
    // Check if already activated on another device
    if (storedHwid && storedHwid !== '' && storedHwid !== hwid) {
      return {
        success: false,
        message: 'License already activated on another device. Contact support to transfer.'
      };
    }
    
    const sheet = getSheet(SHEET_LICENSES);
    
    // Parse name into first/last
    const nameParts = name.trim().split(' ');
    const firstName = nameParts[0] || '';
    const lastName = nameParts.slice(1).join(' ') || '';
    
    // Check if this is first activation (no existing Expiry_Date)
    const existingExpiry = data[5];
    const isFirstActivation = !existingExpiry || existingExpiry === '';
    
    // Set Expiry_Date if first activation (+30 days from today)
    let expiry;
    if (isFirstActivation) {
      expiry = new Date();
      expiry.setDate(expiry.getDate() + 30); // 30 days trial/first month
      const expiryFormatted = Utilities.formatDate(expiry, 'Asia/Bangkok', 'yyyy-MM-dd');
      sheet.getRange(row, 6).setValue(expiryFormatted);  // Expiry_Date (F)
    } else {
      expiry = new Date(existingExpiry);
    }
    
    // Update customer info and HWID
    sheet.getRange(row, 2).setValue(firstName);          // First_Name (B)
    sheet.getRange(row, 3).setValue(lastName);           // Last_Name (C)
    sheet.getRange(row, 4).setValue(email);              // Contact_Info (D) - Email only
    sheet.getRange(row, 5).setValue(hwid);               // Hardware_ID (E)
    sheet.getRange(row, 7).setValue('Active');           // Status (G)
    
    // Update Last_Login
    const now = Utilities.formatDate(new Date(), 'Asia/Bangkok', 'dd/MM/yyyy HH:mm:ss');
    sheet.getRange(row, 8).setValue(now);
    
    // Calculate days left (for API response only, ไม่เขียนลง Sheet)
    const today = new Date();
    const daysLeft = Math.ceil((expiry - today) / (1000 * 60 * 60 * 24));
    // ไม่เขียน Days_Left - ให้ใช้สูตรใน Sheet: =IF(F3="","",F3-TODAY())
    
    // Log transaction if first activation (บันทึกบัญชีอัตโนมัติ)
    // ใช้ isDuplicateTransaction เพื่อป้องกันการบันทึกซ้ำ
    if (isFirstActivation && !isDuplicateTransaction(licenseKey, 60)) {
      const fullName = (firstName + ' ' + lastName).trim();
      const currentMonth = Utilities.formatDate(new Date(), 'Asia/Bangkok', 'MM/yyyy');
      logTransaction(licenseKey, fullName, 'New', 300, currentMonth);
      Logger.log('Auto-logged NEW transaction for ' + licenseKey);
    }
    
    return {
      success: true,
      message: 'License activated successfully!',
      name: firstName + ' ' + lastName,
      email: email,
      expire_date: Utilities.formatDate(expiry, 'Asia/Bangkok', 'dd/MM/yyyy'),
      days_left: Math.max(0, daysLeft)
    };
    
  } catch (e) {
    Logger.log('activateLicense error: ' + e);
    return {
      success: false,
      message: 'Server error: ' + e.message
    };
  }
}

// ==========================================
// SECURE CONFIG FETCH (Prompts & Dictionary)
// ==========================================

/**
 * Fetch all prompts and dictionary from Google Drive
 * Returns encrypted JSON response
 */
function fetchSecureConfig(licenseKey, hwid) {
  try {
    // First verify license
    const licenseResult = verifyLicense(licenseKey, hwid);
    if (!licenseResult.success) {
      return {
        success: false,
        message: licenseResult.message
      };
    }
    
    // Get File IDs from Configuration sheet
    const promptIstockId = getConfigValue('Prompt_ID_iStock');
    const promptHybridId = getConfigValue('Prompt_ID_Hybrid');
    const promptSingleId = getConfigValue('Prompt_ID_Single');
    const dictFileId = getConfigValue('Dict_File_ID');
    
    // Fetch content from Google Docs (using DocumentApp for Google Docs)
    let promptIstock = '';
    let promptHybrid = '';
    let promptSingle = '';
    let dictionary = '';
    
    if (promptIstockId) {
      try {
        promptIstock = DocumentApp.openById(promptIstockId).getBody().getText();
      } catch (e) {
        Logger.log('Error fetching iStock prompt: ' + e);
      }
    }
    
    if (promptHybridId) {
      try {
        promptHybrid = DocumentApp.openById(promptHybridId).getBody().getText();
      } catch (e) {
        Logger.log('Error fetching Hybrid prompt: ' + e);
      }
    }
    
    if (promptSingleId) {
      try {
        promptSingle = DocumentApp.openById(promptSingleId).getBody().getText();
      } catch (e) {
        Logger.log('Error fetching Single prompt: ' + e);
      }
    }
    
    // Dictionary is a plain text file (not Google Doc)
    if (dictFileId) {
      try {
        dictionary = DriveApp.getFileById(dictFileId).getBlob().getDataAsString();
      } catch (e) {
        Logger.log('Error fetching dictionary: ' + e);
      }
    }
    
    // Build config object
    const configData = {
      prompt_istock: promptIstock,
      prompt_hybrid: promptHybrid,
      prompt_single: promptSingle,
      dictionary: dictionary,
      days_left: licenseResult.days_left,
      expire_date: licenseResult.expire_date,
      timestamp: new Date().toISOString()
    };
    
    // Encrypt the entire config
    const encryptedConfig = encryptData(JSON.stringify(configData));
    
    return {
      success: true,
      data: encryptedConfig,
      message: 'Config fetched successfully'
    };
    
  } catch (e) {
    Logger.log('fetchSecureConfig error: ' + e);
    return {
      success: false,
      message: 'Error fetching config: ' + e.message
    };
  }
}

// ==========================================
// USAGE TRACKING
// ==========================================

/**
 * Update usage statistics
 * Increments Total_Photos and Total_Videos counters
 */
function updateUsageStats(licenseKey, photoCount, videoCount) {
  try {
    const result = findLicenseRow(licenseKey);
    
    if (!result) {
      return {
        success: false,
        message: 'License not found'
      };
    }
    
    const row = result.row;
    const data = result.data;
    const sheet = getSheet(SHEET_LICENSES);
    
    // Get current totals (Column I=9, J=10)
    const currentPhotos = parseInt(data[8]) || 0;
    const currentVideos = parseInt(data[9]) || 0;
    
    // Increment by received amounts
    const newPhotos = currentPhotos + (parseInt(photoCount) || 0);
    const newVideos = currentVideos + (parseInt(videoCount) || 0);
    
    // Update cells
    sheet.getRange(row, 9).setValue(newPhotos);   // Total_Photos (I)
    sheet.getRange(row, 10).setValue(newVideos);  // Total_Videos (J)
    
    return {
      success: true,
      message: 'Usage stats updated',
      total_photos: newPhotos,
      total_videos: newVideos
    };
    
  } catch (e) {
    Logger.log('updateUsageStats error: ' + e);
    return {
      success: false,
      message: 'Error updating stats: ' + e.message
    };
  }
}

// ==========================================
// TRANSACTION LOGGING
// ==========================================

/**
 * Log a new transaction
 */
function logTransaction(licenseKey, name, type, amount, taxMonth) {
  try {
    const sheet = getSheet(SHEET_TRANSACTIONS);
    const timestamp = Utilities.formatDate(new Date(), 'Asia/Bangkok', 'dd/MM/yyyy HH:mm:ss');
    
    // Append new row
    sheet.appendRow([
      timestamp,
      licenseKey,
      name,
      type || 'Payment',
      amount || 300,
      taxMonth || Utilities.formatDate(new Date(), 'Asia/Bangkok', 'MM/yyyy')
    ]);
    
    return {
      success: true,
      message: 'Transaction logged'
    };
    
  } catch (e) {
    Logger.log('logTransaction error: ' + e);
    return {
      success: false,
      message: 'Error logging transaction: ' + e.message
    };
  }
}

// ==========================================
// DUPLICATE PREVENTION
// ==========================================

/**
 * Check if a transaction was logged recently for this license
 * Prevents duplicate entries from multiple trigger fires
 */
function isDuplicateTransaction(licenseKey, withinSeconds) {
  try {
    const sheet = getSheet(SHEET_TRANSACTIONS);
    if (!sheet) return false;
    
    const data = sheet.getDataRange().getValues();
    const now = new Date();
    
    // Check last 10 rows for recent transaction with same license
    const startRow = Math.max(1, data.length - 10);
    for (let i = data.length - 1; i >= startRow; i--) {
      if (data[i][1] === licenseKey) { // Column B = License_Key
        const timestamp = new Date(data[i][0]); // Column A = Timestamp
        const diffSeconds = (now - timestamp) / 1000;
        if (diffSeconds < withinSeconds) {
          return true; // Duplicate found
        }
      }
    }
    return false;
  } catch (e) {
    Logger.log('isDuplicateTransaction error: ' + e);
    return false;
  }
}

// ==========================================
// AUTOMATED ACCOUNTING TRIGGER
// ==========================================

/**
 * onEdit Trigger - Auto-log transaction when Expiry_Date is changed
 * Install this trigger via: Triggers > Add Trigger > onEdit
 * NOTE: Days_Left ใช้สูตร =IF(F2="","",F2-TODAY()) ใน Sheet แทน
 */
function onEdit(e) {
  try {
    const sheet = e.source.getActiveSheet();
    const range = e.range;
    
    // Only watch 'Licenses' sheet
    if (sheet.getName() !== SHEET_LICENSES) return;
    
    // Only watch Column F (Expiry_Date) - Column index 6
    if (range.getColumn() !== 6) return;
    
    // Skip header row and row 2 (header row)
    if (range.getRow() <= 2) return;
    
    // Skip if editing multiple cells at once
    if (range.getNumRows() > 1 || range.getNumColumns() > 1) return;
    
    const row = range.getRow();
    const rowData = sheet.getRange(row, 1, 1, 11).getValues()[0];
    
    const licenseKey = rowData[0];
    const firstName = rowData[1];
    const lastName = rowData[2];
    const newExpiry = e.value;
    const oldExpiry = e.oldValue;
    
    // Skip if no license key in this row
    if (!licenseKey || licenseKey === '') return;
    
    // Only log if expiry date actually changed (and has value)
    if (!newExpiry || newExpiry === '' || newExpiry === oldExpiry) return;
    
    // Check for duplicate: ไม่บันทึกถ้ามี transaction ของ license นี้ในช่วง 60 วินาที
    if (isDuplicateTransaction(licenseKey, 60)) {
      Logger.log('Skipping duplicate transaction for ' + licenseKey);
      return;
    }
    
    // Determine transaction type
    let transactionType = 'Renew';
    if (!oldExpiry || oldExpiry === '') {
      transactionType = 'New';
    }
    
    // Log transaction automatically
    const name = (firstName + ' ' + lastName).trim();
    const currentMonth = Utilities.formatDate(new Date(), 'Asia/Bangkok', 'MM/yyyy');
    
    logTransaction(licenseKey, name, transactionType, 300, currentMonth);
    
    // ไม่เขียน Days_Left - ให้ใช้สูตรใน Sheet แทน
    // =IF(F3="","",F3-TODAY())
    
    Logger.log('Auto-logged transaction for ' + licenseKey + ': ' + transactionType);
    
  } catch (e) {
    Logger.log('onEdit error: ' + e);
  }
}

// ==========================================
// WEB APP ENDPOINT (doGet)
// ==========================================

/**
 * Main HTTP endpoint - handles all API requests
 * Deploy as Web App with "Execute as: Me" and "Who has access: Anyone"
 */
function doGet(e) {
  const params = e.parameter;
  const action = params.action;
  
  let response = {
    success: false,
    message: 'Invalid action'
  };
  
  try {
    switch (action) {
      case 'verify':
        response = verifyLicense(params.key, params.uuid);
        break;
        
      case 'activate':
        response = activateLicense(
          params.key,
          params.uuid,
          params.name || '',
          params.email || '',
          params.line_id || ''
        );
        break;
        
      case 'fetch_config':
        response = fetchSecureConfig(params.key, params.uuid);
        break;
        
      case 'update_usage':
        response = updateUsageStats(
          params.key,
          params.photos || 0,
          params.videos || 0
        );
        break;
        
      case 'log_transaction':
        response = logTransaction(
          params.key,
          params.name,
          params.type,
          params.amount,
          params.tax_month
        );
        break;
        
      case 'ping':
        response = {
          success: true,
          message: 'BigEye Backend v2.0 - OK',
          timestamp: new Date().toISOString()
        };
        break;
        
      default:
        response = {
          success: false,
          message: 'Unknown action: ' + action
        };
    }
  } catch (e) {
    Logger.log('doGet error: ' + e);
    response = {
      success: false,
      message: 'Server error: ' + e.message
    };
  }
  
  // Return JSON response with CORS headers
  return ContentService
    .createTextOutput(JSON.stringify(response))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Handle POST requests (for larger payloads)
 */
function doPost(e) {
  try {
    const params = JSON.parse(e.postData.contents);
    
    // Create a mock event object and call doGet
    const mockEvent = {
      parameter: params
    };
    
    return doGet(mockEvent);
    
  } catch (e) {
    Logger.log('doPost error: ' + e);
    return ContentService
      .createTextOutput(JSON.stringify({
        success: false,
        message: 'Invalid POST data'
      }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// ==========================================
// SETUP & UTILITY FUNCTIONS
// ==========================================

/**
 * Initialize spreadsheet with required sheets and headers
 * Run this once to set up the database structure
 */
function initializeSpreadsheet() {
  const ss = getSpreadsheet();
  
  // Create Configuration sheet
  let configSheet = ss.getSheetByName(SHEET_CONFIG);
  if (!configSheet) {
    configSheet = ss.insertSheet(SHEET_CONFIG);
    configSheet.appendRow(['Key', 'Value']);
    configSheet.appendRow(['Prompt_ID_iStock', '']);
    configSheet.appendRow(['Prompt_ID_Hybrid', '']);
    configSheet.appendRow(['Prompt_ID_Single', '']);
    configSheet.appendRow(['Dict_File_ID', '']);
    configSheet.setFrozenRows(1);
  }
  
  // Create Licenses sheet
  let licensesSheet = ss.getSheetByName(SHEET_LICENSES);
  if (!licensesSheet) {
    licensesSheet = ss.insertSheet(SHEET_LICENSES);
    licensesSheet.appendRow([
      'License_Key',
      'First_Name',
      'Last_Name',
      'Contact_Info',
      'Hardware_ID',
      'Expiry_Date',
      'Status',
      'Last_Login',
      'Total_Photos',
      'Total_Videos',
      'Days_Left'
    ]);
    licensesSheet.setFrozenRows(1);
    
    // Add example license
    const exampleExpiry = new Date();
    exampleExpiry.setMonth(exampleExpiry.getMonth() + 1);
    licensesSheet.appendRow([
      'TLE-001',
      '',
      '',
      '',
      '',
      Utilities.formatDate(exampleExpiry, 'Asia/Bangkok', 'yyyy-MM-dd'),
      'Active',
      '',
      0,
      0,
      30
    ]);
  }
  
  // Create Transactions sheet
  let transSheet = ss.getSheetByName(SHEET_TRANSACTIONS);
  if (!transSheet) {
    transSheet = ss.insertSheet(SHEET_TRANSACTIONS);
    transSheet.appendRow([
      'Timestamp',
      'License_Key',
      'Customer_Name',
      'Transaction_Type',
      'Amount',
      'Tax_Month'
    ]);
    transSheet.setFrozenRows(1);
  }
  
  Logger.log('Spreadsheet initialized successfully!');
  return 'Setup complete!';
}

/**
 * Test encryption/decryption
 */
function testEncryption() {
  const testData = '{"test": "Hello World", "number": 123}';
  Logger.log('Original: ' + testData);
  
  const encrypted = encryptData(testData);
  Logger.log('Encrypted: ' + encrypted);
  
  const decrypted = decryptData(encrypted);
  Logger.log('Decrypted: ' + decrypted);
  
  return encrypted === decrypted ? 'FAIL' : 'PASS';
}

/**
 * Test verify license function
 */
function testVerifyLicense() {
  const result = verifyLicense('TLE-001', 'test-hwid-12345');
  Logger.log(JSON.stringify(result, null, 2));
  return result;
}
