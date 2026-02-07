# BigEye Pro: Desktop App UI/UX Blueprint

## 1. Design Philosophy: "The Glass Cockpit"
* **Core Concept:** A Focus-Driven Interface. Minimize distraction, maximize clarity.
* **Visual Style:** Deep Dark Mode (Matte Finish), Minimalist, Professional.
* **Layout Strategy:** 3-Panel Layout (Header / Configuration / Workspace).
* **Target Framework:** Python (Flet or CustomTkinter).

---

## 2. Color Palette & Typography
* **Background:** `#111315` (Deep Charcoal / Obsidian)
* **Surface/Cards:** `#1A1D1F` (Lighter Charcoal for containers)
* **Primary Accent:** `#2D68FF` (Neon Blue - for primary actions/active states)
* **Secondary Accent:** `#00C853` (Success Green - for license/status)
* **Text (Primary):** `#FFFFFF` (White)
* **Text (Secondary):** `#6F767E` (Dim Grey - for labels/inactive text)
* **Border:** `#272B30` (Subtle dark borders)
* **Font:** 'Sarabun' (Thai/English support), Sans-Serif, Clean.

---

## 3. Layout Structure (Grid System)

The application window is divided into three vertical zones:

### Zone A: The Header (Top Bar)
* **Height:** Fixed, approx 60px.
* **Left:** Logo Text ("BigEye" in Bold White + "PRO" in Blue superscript).
* **Right:**
    * **License Badge:** A pill-shaped badge showing status (e.g., "Active" with a green dot). Tooltip shows expiry date.
    * **Settings Icon (Cogwheel):** Opens a modal for API Key & Global Config.

### Zone B: The Command Center (Main Split View)
Occupies the remaining height. Split ratio: 30% Left (Config) : 70% Right (Workspace).

#### Left Panel: Configuration (The Settings Deck)
* **Container Style:** Card-like, rounded corners, distinct background color (`#1A1D1F`).
* **Elements:**
    1.  **Platform Selector:** Segmented Control (Toggle) spanning full width.
        * [Option 1: Adobe & Shutterstock]
        * [Option 2: iStock]
    2.  **Dynamic Options:**
        * If *Adobe* is selected -> Show "Keyword Style" Dropdown (Hybrid vs Single).
        * If *iStock* is selected -> Hide Keyword Style, Show subtle "DB Active" indicator.
    3.  **AI Model:** Simple Dropdown (Default: Gemini 2.0 Flash).
    4.  **Constraints (Sliders):**
        * Title Length (e.g., 50-200)
        * Description Length (e.g., 100-500)
        * Keywords Count (e.g., 10-50)
        * *UX Note:* Show the numeric value explicitly next to the label.
    5.  **Performance:** Thread count slider (1-8).

#### Right Panel: Workspace (The Action Zone)
* **Element 1: The Drop Zone (Center Stage)**
    * Large rectangular area with dashed borders.
    * **State - Idle:** Icon (Folder) + Text "Drag Folder Here".
    * **State - Selected:** Border turns Blue. Text shows Path + File Stats (e.g., "📸 50 Photos | 🎥 10 Videos").
* **Element 2: Primary Action Button**
    * Full-width or Large Floating button below the Drop Zone.
    * **Style:** Gradient Blue background.
    * **Text:** "GENERATE METADATA" (Change to "STOP" in Red when processing).

### Zone C: Activity Monitor (Bottom/Overlay)
* **Location:** Integrated at the bottom of Right Panel or a thin footer.
* **Components:**
    * **Progress Bar:** Smooth linear indicator.
    * **Log Feed:** Minimal list showing current file being processed (e.g., "Analyzing image_01.jpg...").
    * **Status:** "Idle" / "Processing" / "Completed".

---

## 4. Modal Windows (Popups)

### Settings Modal (Triggered by Header Icon)
* **Purpose:** Hide infrequent settings to keep main UI clean.
* **Fields:**
    * Google API Key Input (Password field).
    * "Save" and "Clear" buttons.
    * "Check Balance" button (Optional).

---

## 5. User Interaction Flow & States

1.  **Launch:** App opens in "Idle" state. API Key checks in background.
2.  **Setup:** User selects Platform (e.g., Adobe) -> Left Panel adjusts options automatically.
3.  **Input:** User drags a folder into the **Drop Zone**.
    * *System Action:* Scans folder, filters valid files, ignores proxies.
    * *UI Update:* Drop Zone shows file counts. "Generate" button becomes active (Enabled).
4.  **Action:** User clicks **"GENERATE METADATA"**.
    * *UI Update:* Button turns Red ("STOP").
    * *Proxy Phase:* If videos exist, show overlay "Creating Proxies...".
    * *AI Phase:* Progress bar moves. Log feed updates filenames.
5.  **Completion:**
    * **Success State:** Main area shows "Summary Report" (Total/Success/Error).
    * **Action:** "Open Output Folder" button appears.
    * **Sound:** Play notification sound.

---

## 6. Functional Requirements (Backend Logic)
* **Proxy System:** Auto-generate 480p proxies for video files before sending to AI (temp folder).
* **Thread Safety:** Use background threads for AI processing to keep UI responsive.
* **File Handling:** Filter only valid image/video extensions. Ignore files starting with `proxy_`.
* **Output:** Generate specific CSV formats based on the selected Platform (Adobe/SS vs iStock).