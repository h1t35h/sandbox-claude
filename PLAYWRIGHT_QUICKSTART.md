# Playwright + MCP Quick Start Guide

## Overview

Your sandbox-claude environment now includes:
- ✅ Playwright browser automation (Chromium, Firefox, WebKit)
- ✅ MCP (Model Context Protocol) server for Claude integration
- ✅ Both Python and Node.js Playwright APIs
- ✅ Example scripts ready to run

## Getting Started

### 1. Build the Docker Image

First, build the updated Docker image with Playwright support:

```bash
make docker-build
```

This will take 5-10 minutes on first build as it downloads and installs browsers.

### 2. Create a New Sandbox

```bash
sandbox-claude new -p myproject -f playwright-test
```

### 3. Verify Playwright Installation

Inside the container, verify Playwright is ready:

```bash
# Check Python Playwright
python3 -c "import playwright; print('✓ Python Playwright ready')"

# Check Node.js Playwright
npx playwright --version

# Check MCP configuration
cat $CLAUDE_CONFIG_DIR/mcp-config.json
```

## Running Examples

### Python Example

```bash
cd /workspace
python3 examples/playwright_example.py
```

This will:
- Launch a headless Chromium browser
- Navigate to example.com
- Take a screenshot
- Extract page content
- Save results to `/workspace/screenshot.png`

### Node.js Example

```bash
cd /workspace
node examples/playwright_example.js
```

Similar to Python example but using Node.js API.

## Using MCP with Claude

The MCP server allows Claude to control browser automation directly.

### Example Conversations

**1. Basic Navigation & Screenshot**
```
You: "Navigate to https://news.ycombinator.com and take a screenshot"
```

Claude will use the MCP tools to:
- Call `navigate` with the URL
- Call `screenshot` to capture the page
- Return the screenshot path

**2. Web Scraping**
```
You: "Go to example.com and extract all the text from the h1 tag"
```

Claude will:
- Navigate to the site
- Use `get_text` to extract the heading
- Return the extracted text

**3. Form Interaction**
```
You: "Go to google.com and search for 'playwright testing'"
```

Claude will:
- Navigate to Google
- Use `fill` to enter search text
- Use `click` to submit the form
- Wait for results

## MCP Tools Reference

| Tool | Description | Example Use |
|------|-------------|-------------|
| `navigate` | Go to URL | Navigate to website |
| `screenshot` | Capture page | Take visual snapshots |
| `click` | Click element | Click buttons/links |
| `fill` | Fill input | Enter form data |
| `get_text` | Extract text | Scrape content |
| `get_html` | Get HTML | Get page source |
| `wait_for_selector` | Wait for element | Handle dynamic content |
| `evaluate` | Run JavaScript | Execute custom scripts |

## Common Use Cases

### 1. Web Scraping

**Scrape Product Prices:**
```
You: "Navigate to amazon.com, search for 'laptop', and extract the prices of the first 5 products"
```

### 2. Automated Testing

**Test Login Flow:**
```
You: "Go to my-app.com/login, fill in username 'test@example.com', password 'testpass', and click login"
```

### 3. Visual Regression

**Capture Screenshots:**
```
You: "Take full-page screenshots of example.com in both light and dark mode"
```

### 4. Data Collection

**Gather Information:**
```
You: "Visit the top 10 tech news sites and extract their headlines"
```

## Manual Playwright Usage

### Python Script

Create a new file `my_script.py`:

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Your automation here
    page.goto("https://example.com")
    title = page.title()
    print(f"Page title: {title}")

    # Take screenshot
    page.screenshot(path="my_screenshot.png")

    browser.close()
```

Run it:
```bash
python3 my_script.py
```

### Node.js Script

Create `my_script.js`:

```javascript
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Your automation here
  await page.goto('https://example.com');
  const title = await page.title();
  console.log(`Page title: ${title}`);

  // Take screenshot
  await page.screenshot({ path: 'my_screenshot.png' });

  await browser.close();
})();
```

Run it:
```bash
node my_script.js
```

## Advanced Configuration

### Using Different Browsers

**Python:**
```python
# Use Firefox instead of Chromium
browser = p.firefox.launch(headless=True)

# Use WebKit
browser = p.webkit.launch(headless=True)
```

**Node.js:**
```javascript
const { firefox, webkit } = require('playwright');

// Use Firefox
const browser = await firefox.launch({ headless: true });

// Use WebKit
const browser = await webkit.launch({ headless: true });
```

### Headed Mode (with Display)

For debugging, you can run in headed mode with xvfb:

```bash
# Install xvfb (already included in Docker image)
xvfb-run python3 my_script.py
```

### Custom MCP Server

To extend the MCP server with custom tools, edit:
```bash
/mcp-servers/mcp-playwright-server.py
```

Add new tool definitions to the `@app.list_tools()` function and handlers to `@app.call_tool()`.

## Troubleshooting

### Browser Not Found

If Playwright can't find browsers:
```bash
python3 -m playwright install --with-deps chromium firefox webkit
```

### MCP Server Not Working

Check the configuration:
```bash
cat $CLAUDE_CONFIG_DIR/mcp-config.json
python3 /mcp-servers/mcp-playwright-server.py --help
```

### Permission Errors

Ensure scripts are executable:
```bash
chmod +x /mcp-servers/mcp-playwright-server.py
```

### Import Errors

Verify packages are installed:
```bash
pip list | grep playwright
npm list -g | grep playwright
```

## Testing the Setup

Run the built-in test:
```bash
make test-playwright
```

Or manually:
```bash
# Test Python
python3 -c "from playwright.sync_api import sync_playwright; print('✓ Working')"

# Test Node.js
node -e "require('playwright'); console.log('✓ Working')"

# Test MCP server
python3 /mcp-servers/mcp-playwright-server.py &
# Press Ctrl+C to stop
```

## Resources

- **Playwright Documentation**: https://playwright.dev/
- **Python API**: https://playwright.dev/python/
- **Node.js API**: https://playwright.dev/
- **MCP Protocol**: https://modelcontextprotocol.io/
- **Examples**: `/workspace/examples/`
- **MCP Usage Guide**: `/workspace/examples/MCP_USAGE.md`

## Next Steps

1. ✅ Build the Docker image with `make docker-build`
2. ✅ Create a sandbox with Playwright support
3. ✅ Run the example scripts
4. ✅ Try using MCP tools with Claude
5. ✅ Build your own automation scripts

Happy automating! 🎭
