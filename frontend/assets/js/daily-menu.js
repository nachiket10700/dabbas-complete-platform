// Daily Menu JavaScript

class DailyMenuManager {
    constructor() {
        this.currentDate = new Date().toISOString().split('T')[0];
        this.currentMealType = 'lunch';
        this.menuItems = [];
        this.templates = [];
        this.settings = {};
    }
    
    async init() {
        await this.loadSettings();
        await this.loadDates();
        await this.loadTemplates();
        this.checkDeadline();
        this.render();
    }
    
    async loadSettings() {
        try {
            const response = await fetch('/api/provider/menu-settings');
            const data = await response.json();
            if (data.success) {
                this.settings = data.settings;
            }
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }
    
    async loadDates() {
        try {
            const response = await fetch('/api/provider/upcoming-dates');
            const data = await response.json();
            if (data.success) {
                this.renderDates(data.dates);
            }
        } catch (error) {
            console.error('Error loading dates:', error);
        }
    }
    
    async loadTemplates() {
        try {
            const response = await fetch('/api/provider/menu-templates');
            const data = await response.json();
            if (data.success) {
                this.templates = data.templates;
                this.renderTemplates();
            }
        } catch (error) {
            console.error('Error loading templates:', error);
        }
    }
    
    async loadMenu() {
        try {
            const response = await fetch(`/api/provider/daily-menu/${this.currentDate}/${this.currentMealType}`);
            const data = await response.json();
            if (data.success && data.menu) {
                this.menuItems = data.menu.items;
                document.getElementById('cutoffTime').value = data.menu.cutoff_time;
            } else {
                this.menuItems = [];
            }
            this.renderMenuItems();
        } catch (error) {
            console.error('Error loading menu:', error);
        }
    }
    
    checkDeadline() {
        const now = new Date();
        const deadline = new Date(this.currentDate + 'T10:00:00');
        const warning = document.getElementById('deadlineWarning');
        const saveBtn = document.querySelector('.btn-save');
        
        if (now > deadline) {
            warning.style.display = 'flex';
            if (saveBtn) saveBtn.disabled = true;
        } else {
            warning.style.display = 'none';
            if (saveBtn) saveBtn.disabled = false;
        }
    }
    
    renderDates(dates) {
        const container = document.getElementById('dateGrid');
        if (!container) return;
        
        container.innerHTML = dates.map(d => `
            <div class="date-card ${d.date === this.currentDate ? 'selected' : ''} 
                       ${!d.can_upload_lunch ? 'disabled' : ''}"
                 onclick="menuManager.selectDate('${d.date}', ${d.can_upload_lunch})">
                <div class="day">${d.day}</div>
                <div class="date">${d.date}</div>
            </div>
        `).join('');
    }
    
    renderTemplates() {
        const container = document.getElementById('templatesList');
        if (!container) return;
        
        container.innerHTML = this.templates.map(t => `
            <span class="template-badge ${t.is_default ? 'default' : ''}" 
                  onclick="menuManager.loadTemplate('${t.id}')">
                <i class="fas fa-copy"></i> ${t.name}
            </span>
        `).join('');
    }
    
    renderMenuItems() {
        const container = document.getElementById('menuItems');
        if (!container) return;
        
        container.innerHTML = this.menuItems.map((item, index) => `
            <div class="menu-item">
                <div class="menu-item-header">
                    <h4>Item ${index + 1}</h4>
                    <i class="fas fa-times remove-item" onclick="menuManager.removeItem(${index})"></i>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label>Item Name</label>
                        <input type="text" value="${item.name || ''}" 
                               onchange="menuManager.updateItem(${index}, 'name', this.value)">
                    </div>
                    <div class="form-group">
                        <label>Price (₹)</label>
                        <input type="number" value="${item.price || ''}" 
                               onchange="menuManager.updateItem(${index}, 'price', this.value)">
                    </div>
                </div>
                
                <div class="form-group">
                    <label>Description</label>
                    <textarea rows="2" onchange="menuManager.updateItem(${index}, 'description', this.value)">${item.description || ''}</textarea>
                </div>
            </div>
        `).join('');
    }
    
    selectDate(date, canUpload) {
        if (!canUpload) return;
        this.currentDate = date;
        this.checkDeadline();
        this.loadMenu();
        this.renderDates();
    }
    
    switchMealType(type) {
        this.currentMealType = type;
        this.loadMenu();
    }
    
    addMenuItem() {
        this.menuItems.push({
            name: '',
            description: '',
            price: '',
            category: 'main',
            is_vegetarian: false,
            is_vegan: false,
            is_gluten_free: false,
            spicy_level: 'medium',
            available_quantity: 10
        });
        this.renderMenuItems();
    }
    
    updateItem(index, field, value) {
        this.menuItems[index][field] = value;
    }
    
    removeItem(index) {
        this.menuItems.splice(index, 1);
        this.renderMenuItems();
    }
    
    async saveMenu() {
        const data = {
            menu_date: this.currentDate,
            meal_type: this.currentMealType,
            cutoff_time: document.getElementById('cutoffTime').value,
            items: this.menuItems
        };
        
        try {
            const response = await fetch('/api/provider/daily-menu', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                alert('Menu published successfully!');
            } else {
                alert(result.error || 'Failed to publish menu');
            }
        } catch (error) {
            console.error('Error saving menu:', error);
            alert('Network error. Please try again.');
        }
    }
}

// Initialize on page load
let menuManager;
document.addEventListener('DOMContentLoaded', () => {
    menuManager = new DailyMenuManager();
    menuManager.init();
});