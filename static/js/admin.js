// Global configuration

let productsCurrentPage = 1;
let licensesCurrentPage = 1;
let productChoices = null;
let productSearchChoices = null;

const API_BASE = '/api';
let token = localStorage.getItem('token');
if (token) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
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
        const response = await axios.get(`${API_BASE}/licenses/stats`);
        const stats = response.data;
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
        const res = await axios.get(`${API_BASE}/products?page=${page}&q=${encodeURIComponent(query)}`);
        const products = res.data.products || [];
        const pagination = res.data.pagination || { page: 1, total: 1 };
        const tbody = document.querySelector('#products-table tbody');
        if(products.length == 0) {
            showNoProducts(); return;
        }        
        tbody.innerHTML = products.map(product => `
            <tr>
                <td><strong>${product.name}</strong></td>
                <td>${product.description || ''}</td>
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
        const res = await axios.get(`${API_BASE}/auth/users?page=${page}`);
        const users = res.data.users || [];
        const pagination = res.data.pagination || { page: 1, total: 1 };
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
            <tr>
                <td>${no++}</td>
                <td>${user.username}</td>
                <td>${user.first_name || ''}&nbsp;${user.last_name || ''}</td>                
                <td>  
                    <span class="badge bg-${changeRoleToStatus(user.role)}">
                        ${user.role}
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
        showAlert(error.response?.data?.error || 'Failed to change user role', 'danger');
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
        showAlert( error.response?.data?.error ||'Failed to delete user', 'danger');
    }

}

// Load licenses table
async function loadLicenses(page = 1 , query = '') {
    try {
        showProductsLoading();
        const res = await axios.get(`${API_BASE}/licenses?page=${page}&q=${encodeURIComponent(query)}`);
        const licenses = res.data.licenses || [];
        const pagination = res.data.pagination || { page: 1, total: 1 };
        const tbody = document.querySelector('#licenses-table tbody');
        const noDataDiv = document.getElementById('licenses-no-data');
        if(tbody === null) return;
        if(licenses.length == 0) {
            showNoProducts(); return;
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
                        ${license.status}
                    </span>
                </td>
                <td>
                    ${license.expires_at ? 
                        new Date(license.expires_at).toLocaleDateString() : 
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
        const response = await axios.post(`${API_BASE}/licenses`, {
            product_id: parseInt(productId),
            user_id: userId,
            credit_number: credit_number || 'None',
            machine_code: machine_code || 'None',
            expires_days: parseInt(expiresHours)
        });
        
        const result = response.data;
        showAlert(`License created: ${result.license_key}`, 'success');
        
        // Reset form and reload data
        document.getElementById('user-id').value = '';
        await loadLicenses();
        await loadProducts();
        await loadStats();
        
    } catch (error) {
        showAlert(error.response?.data?.error || 'Failed to create license', 'danger');
    }
}

async function backupLicenses() {
    try {
        const response = await axios.get(`${API_BASE}/licenses/backup`, {
            responseType: 'blob'
        });
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `licenses_backup_${new Date().toISOString().slice(0,10)}.xlsx`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showAlert('License backup downloaded', 'success');
        
    } catch (error) {
        showAlert(error.response?.data?.error || 'Failed to backup licenses', 'danger');
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
        const response = await axios.post(`${API_BASE}/products`, {
            name: name,
            description: description || null,
            max_devices: parseInt(maxDevices)
        });
        
        showAlert('Product created successfully!', 'success');
        bootstrap.Modal.getInstance(document.getElementById('productModal')).hide();
        
        // Reset form
        document.getElementById('product-form').reset();
        
        // Reload products
        await loadProducts();
        await updateProductSelect();
        
    } catch (error) {
        showAlert(error.response?.data?.error || 'Failed to create product', 'danger');
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
        showAlert(error.response?.data?.error || 'Failed to revoke license', 'danger');
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
        showAlert(error.response?.data?.error || 'Failed to delete license', 'danger');
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
        const response = await axios.get(`${API_BASE}/products/all`);
        const products = response.data.products;
        const select = document.getElementById('product-select');
        const select_search = document.getElementById('product-search-select');
        if(!select || !select_search) return;
        select.innerHTML = '<option value="">Select Product...</option>' + 
            products.map(product => 
                `<option value="${product.id}">${product.name}</option>`
            ).join('');
        select_search.innerHTML = '<option value="">Select Product...</option>' + 
            products.map(product => 
                `<option value="${product.id}">${product.name}</option>`
            ).join('');
        // Destroy previous Choices instance if exists
        if (productChoices) {
            productChoices.destroy();
        }
        if(productSearchChoices){
            productSearchChoices.destroy();
        }
        // Initialize Choices after options are set
        productChoices = new Choices(select, { searchEnabled: true });
        productSearchChoices = new Choices(select_search, {searchEnabled : true});
    } catch (error) {
        console.error('Failed to update product select:', error);
    }
}

// Show alert messages
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
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
        const response = await axios.get(`${API_BASE}/products`);
        const product = response.data.products.find(p => p.id === productId);
        if (!product) {
            showAlert('Product not found', 'danger');
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
                                    <input type="text" class="form-control" id="edit-product-description" value="${product.description || ''}">
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
                showAlert(error.response?.data?.error || 'Failed to update product', 'danger');
            }
        };

        // Clean up modal after hide
        document.getElementById(modalId).addEventListener('hidden.bs.modal', function () {
            this.remove();
        });

    } catch (error) {
        showAlert('Failed to load product for editing', 'danger');
    }
}

// View product stats
async function viewProductStats(productId) {
    try {
        const response = await axios.get(`${API_BASE}/products/${productId}/stats`);
        const stats = response.data;
        
        // Create modal with stats
        const modal = createStatsModal(`Product Stats: ${stats.product.name}`, stats);
        modal.show();
    } catch (error) {
        showAlert('Failed to load product stats', 'danger');
    }
}

async function removeProduct(productId) {
    if (!confirm('Are you sure you want to delete this product? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await axios.delete(`${API_BASE}/products/${productId}`);
        if (response.data.success) {
            showAlert('Product deleted successfully', 'success');
            await loadProducts();
            await updateProductSelect();
            await loadLicenses();
            await loadStats();
        } else {
            showAlert(response.data.error || 'Failed to delete product', 'danger');
        }
    } catch (error) {
        showAlert(error.response?.data?.error || 'Failed to delete product', 'danger');
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
        console.log(document.getElementById('search-license-input').value);
        const key_search = document.getElementById('search-license-input').value.trim();
        const query = selectedValues + ',' + key_search;
        console.log(query);
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
        const res = await axios.get(`/api/licenses/${licenseKey}`);
        const lic = res.data;
        modalBody.innerHTML = `
            <ul class="list-group">
                <li class="list-group-item"><strong>License Key:</strong> ${lic.key}</li>
                <li class="list-group-item"><strong>Product:</strong> ${lic.product_name}</li>
                <li class="list-group-item"><strong>User:</strong> ${lic.user_id}</li>                
                <li class="list-group-item"><strong>Status:</strong> ${lic.status}</li>
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

// Show loading state for products
function showProductsLoading() {
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