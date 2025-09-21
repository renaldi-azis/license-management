// Global configuration
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
        await loadStats();
        
        // Load products
        await loadProducts();
        
        // Load licenses
        await loadLicenses();
        
        // Setup real-time updates
        setupRealTimeUpdates();
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
        
        // Update cards with animations
        updateStatsAnimation();
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Load products table
async function loadProducts() {
    try {
        const response = await axios.get(`${API_BASE}/products`);
        const products = response.data.products;
        const tbody = document.querySelector('#products-table tbody');
        
        tbody.innerHTML = products.map(product => `
            <tr>
                <td><strong>${product.name}</strong></td>
                <td>${product.description || ''}</td>
                <td>
                    <span class="badge bg-success">${product.active_licenses || 0}</span>
                    <span class="text-muted"> / ${product.total_licenses || 0}</span>
                </td>
                <td>${product.max_devices}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="editProduct(${product.id})">
                        Edit
                    </button>
                    <button class="btn btn-sm btn-outline-success" onclick="viewProductStats(${product.id})">
                        Stats
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load products:', error);
    }
}

// Load licenses table
async function loadLicenses(page = 1) {
    try {
        const response = await axios.get(`${API_BASE}/licenses?page=${page}`);
        const licenses = response.data.licenses;
        const tbody = document.querySelector('#licenses-table tbody');
        
        tbody.innerHTML = licenses.map(license => `
            <tr class="fade-in">
                <td>
                    <code class="license-key">${license.key_display}</code>
                    <button class="btn btn-sm btn-outline-secondary ms-2" 
                            onclick="copyLicenseKey('${license.key_display}')" 
                            title="Copy key">
                        📋
                    </button>
                </td>
                <td>${license.product_name}</td>
                <td>${license.user_id}</td>
                <td>
                    <span class="status-badge status-${license.status}">
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
                        `<button class="btn btn-sm btn-outline-danger" onclick="revokeLicense('${license.key_display}')">
                            Revoke
                        </button>` : 
                        ''
                    }
                    <button class="btn btn-sm btn-outline-info" onclick="viewLicenseDetails('${license.id}')">
                        Details
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load licenses:', error);
    }
}

// Create new license
async function createLicense() {
    const productId = document.getElementById('product-select').value;
    const userId = document.getElementById('user-id').value;
    const expiresDays = document.getElementById('expires-days').value;
    
    if (!productId || !userId) {
        showAlert('Please select a product and enter user ID', 'warning');
        return;
    }
    
    try {
        const response = await axios.post(`${API_BASE}/licenses`, {
            product_id: parseInt(productId),
            user_id: userId,
            expires_days: parseInt(expiresDays)
        });
        
        const result = response.data;
        showAlert(`License created: ${result.license_key}`, 'success');
        
        // Reset form and reload data
        document.getElementById('user-id').value = '';
        await loadLicenses();
        await loadStats();
        
    } catch (error) {
        showAlert(error.response?.data?.error || 'Failed to create license', 'danger');
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

// Copy license key to clipboard
function copyLicenseKey(key) {
    navigator.clipboard.writeText(key).then(() => {
        showAlert('License key copied to clipboard', 'info');
    });
}

// Update product select dropdown
async function updateProductSelect() {
    try {
        const response = await axios.get(`${API_BASE}/products`);
        const products = response.data.products;
        const select = document.getElementById('product-select');
        
        select.innerHTML = '<option value="">Select Product...</option>' + 
            products.map(product => 
                `<option value="${product.id}">${product.name}</option>`
            ).join('');
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
    // Update stats every 30 seconds
    setInterval(loadStats, 30000);
    
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

// View license details (placeholder)
function viewLicenseDetails(licenseId) {
    showAlert('License details view coming soon!', 'info');
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
                                    <li><strong>Total Licenses:</strong> ${stats.license_stats.total_licenses}</li>
                                    <li><strong>Active:</strong> ${stats.license_stats.active_licenses}</li>
                                    <li><strong>Expired:</strong> ${stats.license_stats.expired_licenses}</li>
                                    <li><strong>Revoked:</strong> ${stats.license_stats.revoked_licenses}</li>
                                </ul>
                            </div>
                            <div class="col-md-6">
                                <h6>Usage Statistics</h6>
                                <ul class="list-unstyled">
                                    <li><strong>Average Usage:</strong> ${stats.license_stats.avg_usage?.toFixed(1) || 0}</li>
                                    <li><strong>Max Usage:</strong> ${stats.license_stats.max_usage}</li>
                                    <li><strong>Recent Validations:</strong> ${stats.recent_validations}</li>
                                    <li><strong>Est. Revenue:</strong> $${stats.estimated_revenue}</li>
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

// Clean up modals on page unload
window.addEventListener('beforeunload', function() {
    document.querySelectorAll('.modal').forEach(modal => modal.remove());
});