// Global configuration

let productsCurrentPage = 1;
let licensesCurrentPage = 1;
let usersCurrentPage = 1;
let settingsCurrentPage = 1;
let productChoices = null;
let productSearchChoices = null;
let productSettingChoices = null;

const API_BASE = '/api';
let client = null;
let token = localStorage.getItem('token');
if (token) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
}

class SecureLicenseClient {
    constructor() {
        this.clientId = 'x-client';
        this.sessionId = null;
        this.aesKey = null;
        this.serverPublicKey = null;
        this.clientKeyPair = null;
    }

   initializeSession  = async () => {
        try {
            const response = await fetch(`/init-session`, {
                method: 'GET',
                headers: {
                    'X-Client-ID': this.clientId
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.sessionId = data.session_id;
                this.serverPublicKey = await this.importPublicKey(data.server_public_key);
                axios.defaults.headers.common['X-Session-ID'] = `${this.sessionId}`;
                return true;
            }
            return false;
        } catch (error) {
            console.error('Session initialization failed:', error);
            return false;
        }
    }

    // Utility method: Convert base64 string to ArrayBuffer
    base64ToArrayBuffer = (base64) =>{
        const binaryString = atob(base64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes.buffer;
    }

    // Utility method: Convert ArrayBuffer to base64 string
    arrayBufferToBase64 = (buffer) => {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }

    importPublicKey = async (pem) => {
        const pemHeader = '-----BEGIN PUBLIC KEY-----';
        const pemFooter = '-----END PUBLIC KEY-----';
        const pemContents = pem.replace(pemHeader, '').replace(pemFooter, '').replace(/\s/g, '');
        const binaryDer = Uint8Array.from(atob(pemContents), c => c.charCodeAt(0));
        
        return await crypto.subtle.importKey(
            'spki',
            binaryDer,
            {
                name: 'RSA-OAEP',
                hash: 'SHA-256'
            },
            true,
            ['encrypt']
        );
    }

    generateKeyPair = async () => {
        this.clientKeyPair = await crypto.subtle.generateKey(
            {
                name: 'RSA-OAEP',
                modulusLength: 2048,
                publicExponent: new Uint8Array([1, 0, 1]),
                hash: 'SHA-256'
            },
            true,
            ['encrypt', 'decrypt']
        );
    }

    exportPublicKey = async ()=> {
        const exported = await crypto.subtle.exportKey('spki', this.clientKeyPair.publicKey);
        const exportedAsBase64 = btoa(String.fromCharCode(...new Uint8Array(exported)));
        return `-----BEGIN PUBLIC KEY-----\n${exportedAsBase64}\n-----END PUBLIC KEY-----`;
    }

    performKeyExchange = async () => {
        try {
            await this.generateKeyPair();
            this.aesKey = await crypto.subtle.generateKey(
                { name: 'AES-CBC', length: 256 },
                true,
                ['encrypt', 'decrypt']
            );

            const exportedAesKey = await crypto.subtle.exportKey('raw', this.aesKey);
            const encryptedAesKey = await crypto.subtle.encrypt(
                { name: 'RSA-OAEP' },
                this.serverPublicKey,
                exportedAesKey
            );

            const clientPublicKey = await this.exportPublicKey();

            const response = await fetch(`/key-exchange`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    encrypted_aes_key: btoa(String.fromCharCode(...new Uint8Array(encryptedAesKey))),
                    client_public_key: clientPublicKey
                })
            });

            return response.ok;
        } catch (error) {
            console.error('Key exchange failed:', error);
            return false;
        }
    }

    aesEncrypt = async (data) => {
        const iv = crypto.getRandomValues(new Uint8Array(16));
        const dataStr = JSON.stringify(data);
        const encoder = new TextEncoder();
        const dataBytes = encoder.encode(dataStr);

        // PKCS7 padding
        const blockSize = 16;
        const padLength = blockSize - (dataBytes.length % blockSize);
        const padded = new Uint8Array(dataBytes.length + padLength);
        padded.set(dataBytes);
        padded.fill(padLength, dataBytes.length);

        const encrypted = await crypto.subtle.encrypt(
            { name: 'AES-CBC', iv },
            this.aesKey,
            padded
        );

        return {
            iv: btoa(String.fromCharCode(...iv)),
            data: btoa(String.fromCharCode(...new Uint8Array(encrypted)))
        };
    }

   
    aesDecrypt = async (encryptedData) => {
        try {            
            // If it's a string, it's probably base64 encoded JSON
            if (typeof encryptedData === 'string') {
                // Step 1: Base64 decode the string
                const decodedString = atob(encryptedData);
                // Step 2: Parse the JSON
                encryptedData = JSON.parse(decodedString);
            }
            
            // Now decrypt normally
            const iv = this.base64ToArrayBuffer(encryptedData.iv);
            const data = this.base64ToArrayBuffer(encryptedData.data);

            const decrypted = await crypto.subtle.decrypt(
                { name: "AES-CBC", iv: iv },
                this.aesKey,
                data
            );
            
            // Remove padding and return
            const decryptedArray = new Uint8Array(decrypted);
            
            const decoder = new TextDecoder();
            return JSON.parse(decoder.decode(decryptedArray));
            
        } catch (error) {
            console.error('Decryption failed:', error);
            throw error;
        }
    }

    sendEncryptedPostRequest = async (endpoint, data) => {
        try {
            const encryptedRequest = await this.aesEncrypt(data);
            const fullUrl = `${window.location.origin}/api${endpoint}`;
            const response = await axios.post(fullUrl, {
                encryptedRequest
            });
            if (response.ok) {
                const encryptedResponse = await response.json();
                return await this.aesDecrypt(encryptedResponse);
            } else {
                return { error: `Request failed: ${response.status}` };
            }
        } catch (error) {
            throw error
        }
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    if (token) {
        loadDashboard();
    } else {
        window.location.href = '/login';
    }
});



// Load complete dashboard data
async function loadDashboard() {
    try {

        client = new SecureLicenseClient()                
        await client.initializeSession()
        if(await client.performKeyExchange() == false) return;  

        // Load stats
        if(window.location.pathname === '/admin') {
            await loadStats();
            // Setup real-time updates
            setupRealTimeUpdates();
        }

        await updateProductSelect();

        // Load products
        await loadProducts();
        
        // Load licenses
        await loadLicenses();

        // Load Users
        await loadUsers();

        // Load Settings
        await loadSettings();
        

    } catch (error) {
        console.error('Failed to load dashboard:', error);
        if (error.response?.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '/login';
        }
    }
}

// Load statistics cards
async function loadStats() {
    try {
        const res_encrypted = await axios.get(`${API_BASE}/licenses/stats`);
        const encryptedResponse = res_encrypted.data.encrypted_data
        const res = JSON.parse(await client.aesDecrypt(encryptedResponse))
        const stats = res;
        if(document.getElementById('total-licenses') === null) return;
        document.getElementById('total-licenses').textContent = stats.total_licenses;
        document.getElementById('active-licenses').textContent = stats.active_licenses;
        document.getElementById('expired-licenses').textContent = stats.expired_licenses;
        document.getElementById('revoked-licenses').textContent = stats.revoked_licenses;
        
        document.getElementById('active-licenses-percent').textContent = 
            `${((stats.active_licenses / stats.total_licenses) * 100).toFixed(1) | 0}% of total licenses`;
        document.getElementById('expired-licenses-percent').textContent = 
            `${((stats.expired_licenses / stats.total_licenses) * 100).toFixed(1) | 0}% of total licenses`;
        document.getElementById('revoked-licenses-percent').textContent = 
            `${((stats.revoked_licenses / stats.total_licenses) * 100).toFixed(1) | 0}% of total licenses`;

        // Update cards with animations
        updateStatsAnimation();
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Load products table
async function loadProducts(page = 1, query = '') {
    try {
        showProductsLoading();
        const res_encrypted = await axios.get(`${API_BASE}/products?page=${page}&q=${encodeURIComponent(query)}`);
        const encryptedResponse = res_encrypted.data.encrypted_data
        const res = JSON.parse(await client.aesDecrypt(encryptedResponse))
        
        const products = res.products || [];
        const pagination = res.pagination || { page: 1, total: 1 };        
        const tbody = document.querySelector('#products-table tbody');
        
        if(tbody === null) return;
        if(products.length == 0) {
            showNoProducts(); return;
        }        
        tbody.innerHTML = products.map(product => `
            <tr class="fade-in">
                <td><strong>${product.name}</strong></td>
                <td>${(product.description?product.description.slice(0, 50):'') + (product.description?.length > 50?'...':'') || ''}</td>
                <td>
                    <span class="badge bg-${(product.active_licenses || 0) == 0? "danger" : "success" }">${product.active_licenses || 0} / ${product.total_licenses || 0}</span>
                    
                </td>
                <td>${product.max_devices}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="editProduct(${product.id})">
                        Edit
                    </button>
                    <button class="btn btn-sm btn-outline-info" onclick="viewProductStats(${product.id})">
                        Stats
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="removeProduct(${product.id})">
                        Delete
                    </button>
                </td>
            </tr>
        `).join('');
        renderPagination('products-pagination', pagination.page, pagination.total, (p) => {
            productsCurrentPage = p;
            loadProducts(p);
        });
        showProductsTable();
    } catch (error) {
        console.error('Failed to load products:', error);
    }
}

async function loadUsers(page = 1) {
    try{        
        const tbody = document.querySelector('#users-table tbody');
        const noDataDiv = document.getElementById('users-no-data');
        if(tbody === null) return;
        const res_encrypted = await axios.get(`${API_BASE}/auth/users?page=${page}`);
        const encryptedResponse = res_encrypted.data.encrypted_data
        const res = JSON.parse(await client.aesDecrypt(encryptedResponse))        
        const users = res.users || [];
        const pagination = res.pagination || { page: 1, total: 1 };
        if(users.length == 0) {
            document.getElementById('users-table').style.display = 'none';
            document.getElementById('users-pagination').style.display = 'none';
            noDataDiv.style.display = 'block';
        }
        else {
            document.getElementById('users-table').style.display = 'table';
            document.getElementById('users-pagination').style.display = 'flex';
            noDataDiv.style.display = 'none';
        }
        
        let no = 1;
        tbody.innerHTML = users.map(user => `
            <tr class="fade-in">
                <td>${no++}</td>
                <td>${user.username}</td>
                <td>${user.first_name || ''}&nbsp;${user.last_name || ''}</td>                
                <td>  
                    <span class="badge bg-${changeRoleToStatus(user.role)}">
                        ${user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="changeUserRole('${user.username}','${user.role}')">
                        Change Role
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="removeUser('${user.username}')">
                        Delete
                    </button>
                </td>
            </tr>
        `).join('');
            renderPagination('users-pagination', pagination.page, pagination.total, (p) => {
            usersCurrentPage = p;
            loadUsers(p);
        });
        showUsersTable();
    }catch (error) {
        console.error('Failed to load users:', error);
    }
}

function changeRoleToStatus(role){
    if (role === 'admin'){
        return 'danger';
    } else if (role === 'user'){
        return 'success';
    } else {
        return 'secondary';
    }
}

function changeStatus(stat){    
    if (stat === 'active'){
        return 'success';
    } else if (stat === 'expired'){
        return 'warning';
    } else if (stat === 'revoked'){
        return 'danger';
    } else {
        return 'secondary';
    }
}

async function changeUserRole(username,role) {
    // Implement role change logic here
    const newrole = (role == "admin"? "user":"admin");
    try{
        const res = await axios.put(`${API_BASE}/auth/users/${username}/${newrole}`);
        showAlert('User role changed successfully', 'success');
        loadUsers();
    }catch(error){
        showAlert(error.response?.data?.error || 'Failed to change user role', 'error');
    }
}

async function removeUser(username) {
    // Implement user removal logic here
    if (!confirm(`Are you sure you want to delete user ${username}? This action cannot be undone.`)) {
        return;        
    }
    try{
        const res = await axios.delete(`${API_BASE}/auth/users/${username}`);
        showAlert('User deleted successfully', 'success');
        loadUsers();
    }catch(error){
        showAlert( error.response?.data?.error ||'Failed to delete user', 'error');
    }

}

// Load licenses table
async function loadLicenses(page = 1 , query = '') {
    try {
        showLicensesLoading();
        const res_encrypted = await axios.get(`${API_BASE}/licenses?page=${page}&q=${encodeURIComponent(query)}`);
        const encryptedResponse = res_encrypted.data.encrypted_data
        const res = JSON.parse(await client.aesDecrypt(encryptedResponse))
        const licenses = res.licenses || [];
        const pagination = res.pagination || { page: 1, total: 1 };
        const tbody = document.querySelector('#licenses-table tbody');
        
        if(tbody === null) return;
        if(licenses.length == 0) {
            showNoLicenses(); return;
        }        

        tbody.innerHTML = licenses.map(license => `
            <tr class="fade-in">
                <td>
                    <code class="license-key">${license.key_display}</code>
                    <button class="btn btn-sm btn-outline-secondary ms-2" s
                            onclick="copyLicenseKey('${license.key}')" 
                            title="Copy key">
                        📋
                    </button>
                </td>
                <td>${license.product_name}</td>
                <td>${license.user_id}</td>
                <td>
                    <span class="badge bg-${changeStatus(license.status)}">
                        ${license.status.charAt(0).toUpperCase() + license.status.slice(1)}
                    </span>
                </td>
                <td>
                    ${license.expires_at ? 
                        new Date(license.expires_at).toISOString().replace('T', ' ').slice(0, 19) : 
                        'Never'
                    }
                </td>
                <td>${license.usage_count}</td>
                <td>
                    ${license.status === 'active' ? 
                        `<button class="btn btn-sm btn-outline-primary" onclick="revokeLicense('${license.key}')">
                            Revoke
                        </button>` : 
                        ''
                    }
                    <button class="btn btn-sm btn-outline-info" onclick="showLicenseDetail('${license.key}')">
                        Details
                    </button>
                    <button class="btn btn-sm btn-outline-primary" onclick="editLicenseDetail('${license.key}')">
                        &nbsp;Edit&nbsp;
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="removeLicense('${license.key}')">
                        Delete
                    </button>
                </td>
            </tr>
        `).join('');
        renderPagination('licenses-pagination', pagination.page, pagination.total, (p) => {
            licensesCurrentPage = p;
            loadLicenses(p);
        });
        showLicensesTable();
    } catch (error) {
        console.error('Failed to load licenses:', error);
    }
}

// Create new license
async function createLicense() {
    const productId = document.getElementById('product-select').value;
    const userId = document.getElementById('user-id').value;
    const expiresHours = document.getElementById('expires-hours').value;
    const credit_number = document.getElementById('credit-number').value;
    const machine_code = document.getElementById('machine-code').value;
    
    if (!productId || !userId) {
        showAlert('Please select a product and enter userId', 'warning');
        return;
    }
    
    if(!machine_code){
        showAlert('Please enter machine code', 'warning');
        return;
    }

    try {

        const response = await client.sendEncryptedPostRequest('/licenses', {
            product_id: parseInt(productId),
            user_id: userId,
            credit_number: credit_number || 'None',
            machine_code: machine_code || 'None',
            expires_hours: parseInt(expiresHours)
        })
        
        showAlert(`New License created`, 'success');
        
        // Reset form and reload data
        document.getElementById('user-id').value = '';
        document.getElementById('machine-code').value = '';
        
        await loadStats();
        await loadProducts();
        await loadLicenses();
        
        
    } catch (error) {
        showAlert(error.response?.data?.error || 'Failed to create license', 'error');
    }
}

async function backupLicenses() {
    try {
        const res = await axios.get(`${API_BASE}/licenses/backup`, {
            responseType: 'blob'
        });
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `licenses_backup_${new Date().toISOString().slice(0,10)}.xlsx`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showAlert('License backup downloaded', 'success');
        
    } catch (error) {
        showAlert(error.response?.data?.error || 'Failed to backup licenses', 'error');
    }
}

// Create new product
async function createProduct() {
    const name = document.getElementById('product-name').value;
    const description = document.getElementById('product-description').value;
    const maxDevices = document.getElementById('product-max-devices').value;
    
    if (!name) {
        showAlert('Product name is required', 'warning');
        return;
    }
    
    try {        
        const response = await client.sendEncryptedPostRequest('/products', {
            name: name,
            description: description || null,
            max_devices: parseInt(maxDevices)
        })
        if(response)
        {
            showAlert('Product created successfully!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('productModal')).hide();
            
            // Reset form
            document.getElementById('product-form').reset();
            
            // Reload products
            await loadProducts();
            await updateProductSelect();
        }
        
    } catch (error) {
        showAlert(error.response?.data?.error || 'Failed to create product', 'error');
    }
}

// Revoke license
async function revokeLicense(licenseKey) {
    if (!confirm('Are you sure you want to revoke this license?')) {
        return;
    }
    
    try {
        const response = await axios.post(`${API_BASE}/licenses/${licenseKey}/revoke`);
        showAlert('License revoked successfully', 'success');
        await loadLicenses();
        await loadStats();
    } catch (error) {
        showAlert(error.response?.data?.error || 'Failed to revoke license', 'error');
    }
}

// Remove license
async function removeLicense(licenseKey) {
    if (!confirm('Are you sure you want to delete this license? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await axios.delete(`${API_BASE}/licenses/${licenseKey}`);
        showAlert('License deleted successfully', 'success');
        await loadLicenses();
        await loadStats();
    } catch (error) {
        showAlert(error.response?.data?.error || 'Failed to delete license', 'error');
    }
}

// Copy license key to clipboard
function copyLicenseKey(key) {
    if(navigator.clipboard === undefined){
        // Fallback for older browsers and HTTP
        const tempInput = document.createElement('input');
        tempInput.value = key;
        document.body.appendChild(tempInput);
        tempInput.select();
        document.execCommand('copy');
        document.body.removeChild(tempInput);
        showAlert('License key copied', 'success');
        return;
    }
    if (navigator.clipboard) {
        navigator.clipboard.writeText(key)
            .then(() => showAlert('License key copied', 'success'))
            .catch(err => showAlert('Failed to copy license key', 'warning'))
    } else {
        // Fallback for older browsers
        const tempInput = document.createElement('input');
        tempInput.value = key;
        document.body.appendChild(tempInput);
        tempInput.select();
        document.execCommand('copy');
        document.body.removeChild(tempInput);
        showAlert('License key copied', 'success');
    }
}

// Update product select dropdown
async function updateProductSelect() {
    try {
        const res_encrypted = await axios.get(`${API_BASE}/products/all`);
        const encryptedResponse = res_encrypted.data.encrypted_data
        const res = JSON.parse(await client.aesDecrypt(encryptedResponse))
        const products = res.products;
        const select = document.getElementById('product-select');
        const select_search = document.getElementById('product-search-select');
        const setting_select = document.getElementById('setting-product-select');
        
        if(select !== null)
        {
            select.innerHTML = '<option value="">Select Product...</option>' + 
                products.map(product => 
                    `<option value="${product.id}">${product.name}</option>`
                ).join('');
        }
        if(select_search !== null){
            select_search.innerHTML = '<option value="">Select Product...</option>' + 
                products.map(product => 
                    `<option value="${product.id}">${product.name}</option>`
                ).join('');
        }
        if(setting_select !== null)
        {
            setting_select.innerHTML = '<option value="">Select Product...</option>' + 
                products.map(product =>
                    `<option value="${product.id}">${product.name}</option>`
                ).join('');
        }
        // Destroy previous Choices instance if exists
        if (productChoices) {
            productChoices.destroy();
        }
        if(productSearchChoices){
            productSearchChoices.destroy();
        }
        if(productSettingChoices){
            productSettingChoices.destroy();
        }
        // Initialize Choices after options are set
        if(select) productChoices = new Choices(select, { searchEnabled: true });
        if(select_search) productSearchChoices = new Choices(select_search, {searchEnabled : true});
        if(setting_select) productSettingChoices = new Choices(setting_select, {searchEnabled : true});

    } catch (error) {
        console.error('Failed to update product select:', error);
    }
}

// Add CSS animation for progress bar
if (!document.querySelector('#alert-styles')) {
    const style = document.createElement('style');
    style.id = 'alert-styles';
    style.textContent = `
        @keyframes progress {
            from { width: 100%; }
            to { width: 0%; }
        }
        
        .btn-close-custom:hover {
            opacity: 1 !important;
            transform: scale(1.1);
        }
        
        .custom-alert:hover {
            transform: translateX(0) scale(1.02) !important;
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.2) !important;
        }
    `;
    document.head.appendChild(style);
}

// Show alert messages
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    
    // Enhanced styling with smooth animations and modern design
    alertDiv.className = `custom-alert custom-alert-${type} alert-dismissible fade show`;
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 320px;
        max-width: 400px;
        border: none;
        padding: 16px 20px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        backdrop-filter: blur(10px);
        transform: translateX(400px);
        opacity: 0;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        font-family: 'Segoe UI', system-ui, sans-serif;
        font-size: 14px;
        line-height: 1.5;
    `;
    
    // Color schemes for different alert types
    const styles = {
        info: {
            background: 'rgba(59, 130, 246, 0.95)',
            color: 'white',
            icon: ' '
        },
        success: {
            background: 'rgba(34, 197, 94, 0.95)',
            color: 'white',
            icon: ' '
        },
        warning: {
            background: 'rgba(234, 179, 8, 0.95)',
            color: 'white',
            icon: ' '
        },
        error: {
            background: 'rgba(239, 68, 68, 0.95)',
            color: 'white',
            icon: ' '
        }
    };
    
    const style = styles[type] || styles.info;
    
    alertDiv.style.background = style.background;
    alertDiv.style.color = style.color;
    
    alertDiv.innerHTML = `
        <div style="display: flex; align-items: flex-start; gap: 12px;">
            <span style="font-size: 18px; flex-shrink: 0;">${style.icon}</span>
            <div style="flex: 1;">
                <div style="font-weight: 600; margin-bottom: 4px; font-size: 15px;">
                    ${type.charAt(0).toUpperCase() + type.slice(1)}
                </div>
                <div style="opacity: 0.95;">${message}</div>
            </div>
            <button type="button" 
                    class="btn-close-custom" 
                    style="
                        background: none;
                        border: none;
                        color: currentColor;
                        font-size: 18px;
                        cursor: pointer;
                        opacity: 0.7;
                        padding: 4px;
                        margin-left: 8px;
                        transition: opacity 0.2s;
                        flex-shrink: 0;
                    "
                    onclick="this.parentElement.parentElement.remove()">
                ✕
            </button>
        </div>
        <div class="progress-bar" style="
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 0 0 12px 12px;
            overflow: hidden;
        ">
            <div class="progress-fill" style="
                width: 100%;
                height: 100%;
                background: rgba(255, 255, 255, 0.8);
                animation: progress 5s linear forwards;
            "></div>
        </div>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Animate in
    requestAnimationFrame(() => {
        alertDiv.style.transform = 'translateX(0)';
        alertDiv.style.opacity = '1';
    });
    
    // Auto remove after 5 seconds with smooth animation
    const removeAlert = () => {
        alertDiv.style.transform = 'translateX(400px)';
        alertDiv.style.opacity = '0';
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 400);
    };
    
    const timeout = setTimeout(removeAlert, 5000);
    
    // Pause auto-remove on hover
    alertDiv.addEventListener('mouseenter', () => {
        clearTimeout(timeout);
        alertDiv.querySelector('.progress-fill').style.animationPlayState = 'paused';
    });
    
    alertDiv.addEventListener('mouseleave', () => {
        const newTimeout = setTimeout(removeAlert, 5000);
        alertDiv.querySelector('.progress-fill').style.animationPlayState = 'running';
    });
}

// Stats animation
function updateStatsAnimation() {
    document.querySelectorAll('[id$="-licenses"]').forEach(card => {
        card.style.transform = 'scale(1.05)';
        setTimeout(() => {
            card.style.transform = 'scale(1)';
        }, 200);
    });
}

// Setup real-time updates
function setupRealTimeUpdates() {
    // Update stats every 30 minutes
    setInterval(loadStats, 30 * 60 * 1000);
    
    // Listen for visibility change to refresh when tab becomes active
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            loadDashboard();
        }
    });
}

// Edit product: show a modal with current product info and allow update
async function editProduct(productId) {
    try {
        // Fetch current product data        
        const res_encrypted = await axios.get(`${API_BASE}/products`);
        const encryptedResponse = res_encrypted.data.encrypted_data
        const res = JSON.parse(await client.aesDecrypt(encryptedResponse))
        const product = res.products.find(p => p.id === productId);
        if (!product) {
            showAlert('Product not found', 'error');
            return;
        }
        // Create modal HTML
        const modalId = 'editProductModal';
        let modalEl = document.getElementById(modalId);
        if (modalEl) modalEl.remove(); // Remove existing modal if present

        const modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <form id="edit-product-form">
                            <div class="modal-header">
                                <h5 class="modal-title">Edit Product: ${product.name}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label for="edit-product-name" class="form-label">Name</label>
                                    <input type="text" class="form-control" id="edit-product-name" value="${product.name}" required>
                                </div>
                                <div class="mb-3">
                                    <label for="edit-product-description" class="form-label">Description</label>
                                    <textarea class="form-control" id="edit-product-description">${product.description || ''}</textarea>
                                </div>
                                <div class="mb-3">
                                    <label for="edit-product-max-devices" class="form-label">Max Devices</label>
                                    <input type="number" class="form-control" id="edit-product-max-devices" value="${product.max_devices}" min="1" required>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="submit" class="btn btn-primary">Save Changes</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById(modalId));
        modal.show();

        // Handle form submission
        document.getElementById('edit-product-form').onsubmit = async function(e) {
            e.preventDefault();
            try {
                await axios.put(`${API_BASE}/products/${productId}`, {
                    name: document.getElementById('edit-product-name').value,
                    description: document.getElementById('edit-product-description').value,
                    max_devices: parseInt(document.getElementById('edit-product-max-devices').value)
                });
                showAlert('Product updated successfully!', 'success');
                modal.hide();
                await loadProducts();
                await updateProductSelect();
            } catch (error) {
                showAlert(error.response?.data?.error || 'Failed to update product', 'error');
            }
        };

        // Clean up modal after hide
        document.getElementById(modalId).addEventListener('hidden.bs.modal', function () {
            this.remove();
        });

    } catch (error) {
        showAlert('Failed to load product for editing', 'error');
    }
}

// View product stats
async function viewProductStats(productId) {
    try {
        const res_encrypted = await axios.get(`${API_BASE}/products/${productId}/stats`);
        const encryptedResponse = res_encrypted.data.encrypted_data
        const res = JSON.parse(await client.aesDecrypt(encryptedResponse))
        const stats = res;
        
        // Create modal with stats
        const modal = createStatsModal(`Product Stats: ${stats.product.name}`, stats);
        modal.show();
        // Destroy modal
        modal._element.addEventListener('hidden.bs.modal', function () {
            this.remove();
        });
    } catch (error) {
        showAlert('Failed to load product stats', 'error');
    }
}

async function removeProduct(productId) {
    if (!confirm('Are you sure you want to delete this product? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await axios.delete(`${API_BASE}/products/${productId}`);
        if(response){
            showAlert('Product deleted successfully', 'success');
            await loadProducts();
            await updateProductSelect();
            await loadLicenses();
            await loadStats();
        } else {
            showAlert(response.data.error || 'Failed to delete product', 'error');
        }
    } catch (error) {
        showAlert(error.response?.data?.error || 'Failed to delete product', 'error');
    }
}

// Create stats modal
function createStatsModal(title, stats) {
    const modalHtml = `
        <div class="modal fade" id="statsModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${title}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6>License Statistics</h6>
                                <ul class="list-unstyled">
                                    <li><strong>Total Licenses:</strong> ${stats.license_stats.total_licenses || 0}</li>
                                    <li><strong>Active:</strong> ${stats.license_stats.active_licenses || 0}</li>
                                    <li><strong>Expired:</strong> ${stats.license_stats.expired_licenses || 0}</li>
                                    <li><strong>Revoked:</strong> ${stats.license_stats.revoked_licenses || 0}</li>
                                </ul>
                            </div>
                            <div class="col-md-6">
                                <h6>Usage Statistics</h6>
                                <ul class="list-unstyled">
                                    <li><strong>Average Usage:</strong> ${stats.license_stats.avg_usage?.toFixed(1) || 0}</li>
                                    <li><strong>Max Usage:</strong> ${stats.license_stats.max_usage || 0}</li>
                                    <li><strong>Recent Validations:</strong> ${stats.recent_validations || 0}</li>
                                    <li><strong>Est. Revenue:</strong> $${stats.estimated_revenue || 0}</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    return new bootstrap.Modal(document.getElementById('statsModal'));
}

async function logoutAndRedirect() {

    // Remove token from localStorage
    localStorage.removeItem('token');
    // Redirect to /admin (or your desired page)
    
    // const response = await axios.get(`${API_BASE}/auth/logout`);
    window.location.href = '/login';
}

//Enter key event for searching licenses
if(document.getElementById('search-license-input'))
    document.getElementById('search-license-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const select = document.getElementById('product-search-select');
            const selectedValues = Array.from(select.selectedOptions).map(option => option.innerHTML);
            const key_search = e.target.value.trim();
            const query = selectedValues + ',' + key_search;
            loadLicenses(1, query);
        }
    });

if(document.getElementById('search-product-input'))
    document.getElementById('search-product-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const query = e.target.value.trim();
            loadProducts(1, query);
        }
    });

if(document.getElementById('product-search-select'))
    document.getElementById('product-search-select').addEventListener('change',function(e){
        const select = document.getElementById('product-search-select');
        const selectedValues = Array.from(select.selectedOptions).map(option => option.innerHTML);
        const key_search = document.getElementById('search-license-input').value.trim();
        const query = selectedValues + ',' + key_search;
        loadLicenses(1, query);
        return selectedValues;
    })

// Attach to logout link if using JS navigation
document.addEventListener('DOMContentLoaded', function() {
    const logoutLink = document.querySelector('a[href="/api/auth/logout"]');
    if (logoutLink) {
        logoutLink.addEventListener('click', function(e) {
            e.preventDefault();
            fetch('/api/auth/logout', { method: 'POST', credentials: 'include' })
                .then(() => logoutAndRedirect());
        });
    }
});

async function showLicenseDetail(licenseKey) {
    const modalBody = document.getElementById('license-detail-body');
    modalBody.innerHTML = `<div class="text-center text-muted"><i class="fas fa-spinner fa-spin"></i> Loading...</div>`;
    const modal = new bootstrap.Modal(document.getElementById('licenseDetailModal'));
    modal.show();

    try {
        const res_encrypted = await axios.get(`/api/licenses/${licenseKey}`);
        const encryptedResponse = res_encrypted.data.encrypted_data
        const res = JSON.parse(await client.aesDecrypt(encryptedResponse))
        
        const lic = res
        modalBody.innerHTML = `
            <ul class="list-group">
                <li class="list-group-item"><strong>License Key:</strong> ${lic.key}</li>
                <li class="list-group-item"><strong>Product:</strong> ${lic.product_name}</li>
                <li class="list-group-item"><strong>User:</strong> ${lic.user_id}</li>                
                <li class="list-group-item"><strong>Status:</strong> 
                    <span class="badge bg-${changeStatus(lic.status)}">
                        ${lic.status.charAt(0).toUpperCase() + lic.status.slice(1)}
                    </span>
                </td></li>
                <li class="list-group-item"><strong>Credit_Number:</strong> ${lic.credit_number}</li>
                <li class="list-group-item"><strong>Machine_Code:</strong> ${lic.machine_code}</li>
                <li class="list-group-item"><strong>Expires At:</strong> ${lic.expires_at || 'N/A'}</li>
                <li class="list-group-item"><strong>Usage Count:</strong> ${lic.usage_count || 0}</li>
                <li class="list-group-item"><strong>Created At:</strong> ${lic.created_at || 'N/A'}</li>
                <!-- Add more fields as needed -->
            </ul>
        `;
    } catch (err) {
        modalBody.innerHTML = `<div class="alert alert-danger">Failed to load license details.</div>`;
    }
}

async function editLicenseDetail(licenseKey) {
    const modalBody = document.getElementById('license-detail-body');
    modalBody.innerHTML = `<div class="text-center text-muted"><i class="fas fa-spinner fa-spin"></i> Loading...</div>`;
    const modal = new bootstrap.Modal(document.getElementById('licenseDetailModal'));
    modal.show();

    try {
        const res_encrypted = await axios.get(`/api/licenses/${licenseKey}`);
        const encryptedResponse = res_encrypted.data.encrypted_data
        const res = JSON.parse(await client.aesDecrypt(encryptedResponse))
        const lic = res

        console.log(lic)
        const existingDate = new Date(lic.expires_at); // Your existing date
        const datetimelocal = formatToDateTimeLocal(existingDate);
        
        modalBody.innerHTML = `
            <form id="edit-license-form">
                <div class="mb-3">
                    <label for="edit-license-user-id" class="form-label">User ID</label>
                    <input type="text" class="form-control" id="edit-license-user-id" value="${lic.user_id}" required>
                </div>
                <div class="mb-3">
                    <label for="edit-license-expires-at" class="form-label">Expires At (YYYY-MM-DD HH:MM)</label>
                    <input type="datetime-local" class="form-control" id="edit-license-expires-at" value="${datetimelocal || ''}">
                </div>
                <div class="mb-3">
                    <label for="edit-license-credit-number" class="form-label">Credit Number</label>
                    <input type="number" class="form-control" id="edit-license-credit-number" value="${lic.credit_number == 'None'?0:lic.credit_number || 0}">
                </div>
                <button type="submit" class="btn btn-primary">Save Changes</button>
            </form>
        `;

        document.getElementById('edit-license-form').onsubmit = async function(e) {
            e.preventDefault();
            try {
                await axios.put(`${API_BASE}/licenses/${licenseKey}`, {
                    user_id: document.getElementById('edit-license-user-id').value,
                    expires_at: document.getElementById('edit-license-expires-at').value || null,
                    credit_number: document.getElementById('edit-license-credit-number').value || null
                });
                showAlert('License updated successfully!', 'success');
                modal.hide();
                await loadLicenses(licensesCurrentPage);
            } catch (error) {
                showAlert(error.response?.data?.error || 'Failed to update license', 'error');
            }
        };

    } catch (err) {
        modalBody.innerHTML = `<div class="alert alert-danger">Failed to load license details.</div>`;
    }
}

function formatToDateTimeLocal(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function utcToLocalString(utcString) {
    return new Date(utcString).toLocaleString();
}

// Clean up modals on page unload
window.addEventListener('beforeunload', function() {
    document.querySelectorAll('.modal').forEach(modal => modal.remove());
});


// Toggle dropdown menu
document.getElementById('userProfileDropdown').addEventListener('click', function(e) {
    e.stopPropagation();
    const dropdown = document.getElementById('userDropdown');
    dropdown.classList.toggle('show');
});

// Close dropdown when clicking outside
document.addEventListener('click', function() {
    const dropdown = document.getElementById('userDropdown');
    if (dropdown.classList.contains('show')) {
        dropdown.classList.remove('show');
    }
});

// Prevent dropdown from closing when clicking inside it
document.getElementById('userDropdown').addEventListener('click', function(e) {
    e.stopPropagation();
});

// Settings
async function loadSettings(page = 1, query = '') {
    try {
        showSettingsLoading();
        const res_encrypted = await axios.get(`${API_BASE}/settings?page=${page}&q=${encodeURIComponent(query)}`);
        const encryptedResponse = res_encrypted.data.encrypted_data
        const res = JSON.parse(await client.aesDecrypt(encryptedResponse))
        const settings = res.settings || [];
        const pagination = res.pagination || { page: 1, total: 1 };
        const tbody = document.querySelector('#settings-table tbody');
        if(tbody === null) return;
        if(settings.length == 0) {
            showNoSettings(); return;
        }        
        tbody.innerHTML = settings.map(setting => `
            <tr class="fade-in">
                <td><strong>${setting.product_name}</strong></td>
                <td>${setting.number_of_credits}</td>
                <td>${setting.license_duration_hours}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="editSetting('${setting.product_id}')">
                        Edit
                    </button>                    
                </td>
            </tr>
        `).join('');
        renderPagination('settings-pagination', pagination.page, pagination.total, (p) => {
            // No pagination for settings yet
            settingsCurrentPage = p;
            loadSettings(p);
            
        });
        showSettingsTable();
    }catch(error){
        console.error('Failed to load settings:', error);
    }
}

async function createProductSetting() {
    const productId = document.getElementById('setting-product-select').value;
    const numberOfCredits = document.getElementById('setting-number-of-credits').value;
    const licenseDurationHours = document.getElementById('setting-license-duration-hours').value;
    
    if (!productId || !numberOfCredits || !licenseDurationHours) {
        showAlert('Please fill in all fields', 'warning');
        return;
    }
    
    try {
         const response = await client.sendEncryptedPostRequest('/settings', {
            product_id: parseInt(productId),
            number_of_credits: parseInt(numberOfCredits),
            license_duration_hours: parseInt(licenseDurationHours)
        })        

        showAlert('Product setting created successfully!', 'success');
        
        // Reload settings
        await loadSettings();
        
    } catch (error) {
        showAlert(error.response?.data?.error || 'Failed to create product setting', 'error');
    }
}

// Edit product: show a modal with current product info and allow update
async function editSetting(productId) {
    try {
        // Fetch current product data
        const res_encrypted = await axios.get(`${API_BASE}/settings/${productId}`);
        const encryptedResponse = res_encrypted.data.encrypted_data
        const res = JSON.parse(await client.aesDecrypt(encryptedResponse))
        const setting = res;
        if (!setting) {
            showAlert('Setting not found', 'error');
            return;
        }

        // Create modal HTML
        const modalId = 'editSettingModal';
        let modalEl = document.getElementById(modalId);
        if (modalEl) modalEl.remove(); // Remove existing modal if present

        const modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <form id="edit-setting-form">
                            <div class="modal-header">
                                <h5 class="modal-title">Edit Setting: ${setting.product_name}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                
                                <div class="mb-3">
                                    <label for="edit-setting-credit-number" class="form-label">Number of Credits</label>
                                    <input type="text" class="form-control" id="edit-setting-credit-number" value="${setting.number_of_credits || ''}">
                                </div>
                                <div class="mb-3">
                                    <label for="edit-setting-time-duration" class="form-label">Trial Period(h)</label>
                                    <input type="number" class="form-control" id="edit-setting-time-duration" value="${setting.license_duration_hours}" min="1" required>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="submit" class="btn btn-primary">Save Changes</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById(modalId));
        modal.show();

        // Handle form submission
        document.getElementById('edit-setting-form').onsubmit = async function(e) {
            e.preventDefault();
            try {
                await axios.put(`${API_BASE}/settings/${productId}`, {
                    number_of_credits: parseInt(document.getElementById('edit-setting-credit-number').value),
                    license_duration_hours: parseInt(document.getElementById('edit-setting-time-duration').value),
                });
                showAlert('Setting updated successfully!', 'success');
                modal.hide();
                await loadSettings();
            } catch (error) {
                showAlert(error.response?.data?.error || 'Failed to update setting', 'error');
            }
        };

        // Clean up modal after hide
        document.getElementById(modalId).addEventListener('hidden.bs.modal', function () {
            this.remove();
        });

    } catch (error) {
        showAlert('Failed to load setting for editing', 'error');
    }
}

function showSettingsLoading() {
    if(document.getElementById('settings-loading') === null) return;
    document.getElementById('settings-loading').style.display = 'flex';
    document.getElementById('settings-table').style.display = 'none';
    document.getElementById('settings-no-data').style.display = 'none';
    document.getElementById('settings-pagination').style.display = 'none';
}

function showSettingsTable() {
    document.getElementById('settings-loading').style.display = 'none';
    document.getElementById('settings-table').style.display = 'table';
    document.getElementById('settings-no-data').style.display = 'none';
    document.getElementById('settings-pagination').style.display = 'flex';
}

function showNoSettings() {
    document.getElementById('settings-loading').style.display = 'none';
    document.getElementById('settings-table').style.display = 'none';
    document.getElementById('settings-no-data').style.display = 'flex';
    document.getElementById('settings-pagination').style.display = 'none';
}

// Show settings form

// Show loading state for products
function showProductsLoading() {
    if(document.getElementById('products-loading') === null) return;
    document.getElementById('products-loading').style.display = 'flex';
    document.getElementById('products-table').style.display = 'none';
    document.getElementById('products-no-data').style.display = 'none';
    document.getElementById('products-pagination').style.display = 'none';
}

// Show products table
function showProductsTable() {
    document.getElementById('products-loading').style.display = 'none';
    document.getElementById('products-table').style.display = 'table';
    document.getElementById('products-no-data').style.display = 'none';
    document.getElementById('products-pagination').style.display = 'flex';
}

// Show no products state
function showNoProducts() {
    document.getElementById('products-loading').style.display = 'none';
    document.getElementById('products-table').style.display = 'none';
    document.getElementById('products-no-data').style.display = 'flex';
    document.getElementById('products-pagination').style.display = 'none';
}

// Show loading state for licenses
function showLicensesLoading() {
    if(document.getElementById('licenses-loading') === null) return;
    document.getElementById('licenses-loading').style.display = 'flex';
    document.getElementById('licenses-table').style.display = 'none';
    document.getElementById('licenses-no-data').style.display = 'none';
    document.getElementById('licenses-pagination').style.display = 'none';
}

// Show licenses table
function showLicensesTable() {
    document.getElementById('licenses-loading').style.display = 'none';
    document.getElementById('licenses-table').style.display = 'table';
    document.getElementById('licenses-no-data').style.display = 'none';
    document.getElementById('licenses-pagination').style.display = 'flex';
}

// Show no licenses state
function showNoLicenses() {
    document.getElementById('licenses-loading').style.display = 'none';
    document.getElementById('licenses-table').style.display = 'none';
    document.getElementById('licenses-no-data').style.display = 'flex';
    document.getElementById('licenses-pagination').style.display = 'none';
}

function showUsersLoading(){
    if(document.getElementById('users-loading') === null) return;
    document.getElementById('users-loading').style.display = 'flex';
    document.getElementById('users-table').style.display = 'none';
    document.getElementById('users-no-data').style.display = 'none';
    document.getElementById('users-pagination').style.display = 'none';
}

function showUsersTable(){
    document.getElementById('users-loading').style.display = 'none';
    document.getElementById('users-table').style.display = 'table';
    document.getElementById('users-no-data').style.display = 'none';
    document.getElementById('users-pagination').style.display = 'flex';
}

function showNoUsers(){
    
    document.getElementById('users-loading').style.display = 'none';
    document.getElementById('users-table').style.display = 'none';
    document.getElementById('users-no-data').style.display = 'flex';
    document.getElementById('users-pagination').style.display = 'none';
}