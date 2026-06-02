/**
 * seller_format.js
 * Handles product listing form: session persistence, validation, and submission.
 */

'use strict';

// ---------------------------------------------------------------------------
// Dynamic price section visibility
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    const rentalCheckbox  = document.getElementById('rental');
    const purchaseCheckbox = document.getElementById('purchase');

    if (rentalCheckbox) {
        rentalCheckbox.addEventListener('change', togglePriceSections);
    }
    if (purchaseCheckbox) {
        purchaseCheckbox.addEventListener('change', togglePriceSections);
    }

    // Restore values from sessionStorage on page load
    restoreFromSessionStorage();
    togglePriceSections();
});

function togglePriceSections() {
    const rental   = document.getElementById('rental')?.checked;
    const purchase = document.getElementById('purchase')?.checked;

    const rentalSection  = document.getElementById('rentalPriceSection');
    const purchaseSection = document.getElementById('purchasePriceSection');

    if (rentalSection) {
        rentalSection.classList.toggle('hidden', !rental);
    }
    if (purchaseSection) {
        purchaseSection.classList.toggle('hidden', !purchase);
    }
}

// ---------------------------------------------------------------------------
// Create price sections dynamically if not present
// ---------------------------------------------------------------------------
function createRentalPriceSection() {
    const section = document.getElementById('rentalPriceSection');
    if (section) {
        section.classList.remove('hidden');
    }
}

function createPurchasePriceSection() {
    const section = document.getElementById('purchasePriceSection');
    if (section) {
        section.classList.remove('hidden');
    }
}

// ---------------------------------------------------------------------------
// Save current form state to sessionStorage
// ---------------------------------------------------------------------------
function saveToSessionStorage() {
    const productName   = document.getElementById('name')?.value || '';
    const rental        = document.getElementById('rental')?.checked || false;
    const purchase      = document.getElementById('purchase')?.checked || false;
    const rentalPrice   = document.getElementById('rentalPrice')?.value || '';
    const rentalPeriod  = document.getElementById('rentalPeriod')?.value || '';
    const purchasePrice = document.getElementById('purchasePrice')?.value || '';
    const smokingRadio  = document.querySelector('input[name="smoking"]:checked');
    const smokingValue  = smokingRadio ? smokingRadio.value : 'no';
    const color         = document.getElementById('color')?.value || '';
    const category1     = document.getElementById('category1')?.value || '';
    const category2     = document.getElementById('category2')?.value || '';
    const brand         = document.getElementById('brand')?.value || '';
    const explanation   = document.getElementById('explanation')?.value || '';
    const returnEl      = document.querySelector('input[name="returnLocation"]') || document.getElementById('returnLocation');
    const returnLocation = returnEl ? returnEl.value : '';

    sessionStorage.setItem('name', productName);
    sessionStorage.setItem('smoking', smokingValue);
    sessionStorage.setItem('color', color);
    sessionStorage.setItem('category1', category1);
    sessionStorage.setItem('category2', category2);
    sessionStorage.setItem('brand', brand);
    sessionStorage.setItem('explanation', explanation);
    sessionStorage.setItem('returnLocation', returnLocation);

    if (rental) {
        sessionStorage.setItem('rental', 'true');
        sessionStorage.setItem('rentalPrice', rentalPrice);
        sessionStorage.setItem('rentalPeriod', rentalPeriod);
    } else {
        sessionStorage.setItem('rental', 'false');
        sessionStorage.removeItem('rentalPrice');
        sessionStorage.removeItem('rentalPeriod');
    }

    if (purchase) {
        sessionStorage.setItem('purchase', 'true');
        sessionStorage.setItem('purchasePrice', purchasePrice);
    } else {
        sessionStorage.setItem('purchase', 'false');
        sessionStorage.removeItem('purchasePrice');
    }
}

// ---------------------------------------------------------------------------
// Restore saved form state from sessionStorage
// ---------------------------------------------------------------------------
function restoreFromSessionStorage() {
    // Product name
    const name = sessionStorage.getItem('name');
    const nameEl = document.getElementById('name');
    if (name && nameEl) nameEl.value = name;

    // Rental
    const rental = sessionStorage.getItem('rental') === 'true';
    const rentalEl = document.getElementById('rental');
    if (rentalEl) rentalEl.checked = rental;

    if (rental) {
        createRentalPriceSection();
        const rentalPrice = sessionStorage.getItem('rentalPrice');
        const rentalPriceEl = document.getElementById('rentalPrice');
        if (rentalPrice && rentalPriceEl) rentalPriceEl.value = rentalPrice;

        const rentalPeriod = sessionStorage.getItem('rentalPeriod');
        const rentalPeriodEl = document.getElementById('rentalPeriod');
        if (rentalPeriod && rentalPeriodEl) rentalPeriodEl.value = rentalPeriod;
    }

    // Purchase
    const purchase = sessionStorage.getItem('purchase') === 'true';
    const purchaseEl = document.getElementById('purchase');
    if (purchaseEl) purchaseEl.checked = purchase;

    if (purchase) {
        createPurchasePriceSection();
        const purchasePrice = sessionStorage.getItem('purchasePrice');
        const purchasePriceEl = document.getElementById('purchasePrice');
        if (purchasePrice && purchasePriceEl) purchasePriceEl.value = purchasePrice;
    }

    // Smoking
    const smoking = sessionStorage.getItem('smoking');
    if (smoking) {
        const smokingRadio = document.querySelector(`input[name="smoking"][value="${smoking}"]`);
        if (smokingRadio) smokingRadio.checked = true;
    }

    // Color
    const color = sessionStorage.getItem('color');
    const colorEl = document.getElementById('color');
    if (color && colorEl) colorEl.value = color;

    // Category 1 & 2
    const category1 = sessionStorage.getItem('category1');
    const category1El = document.getElementById('category1');
    if (category1 && category1El) category1El.value = category1;

    const category2 = sessionStorage.getItem('category2');
    const category2El = document.getElementById('category2');
    if (category2 && category2El) category2El.value = category2;

    // Brand
    const brand = sessionStorage.getItem('brand');
    const brandEl = document.getElementById('brand');
    if (brand && brandEl) brandEl.value = brand;

    // Explanation
    const explanation = sessionStorage.getItem('explanation');
    const explanationEl = document.getElementById('explanation');
    if (explanation && explanationEl) explanationEl.value = explanation;

    // Return location
    const returnLocation = sessionStorage.getItem('returnLocation');
    const returnEl = document.querySelector('input[name="returnLocation"]') || document.getElementById('returnLocation');
    if (returnLocation && returnEl) returnEl.value = returnLocation;

    // Uploaded image preview (first image)
    const uploadedImages = JSON.parse(sessionStorage.getItem('uploadedImages') || '[]');
    if (uploadedImages.length > 0) {
        const displayImage = document.getElementById('displayImage');
        const imageDisplayArea = document.getElementById('imageDisplayArea');
        const noImageArea = document.getElementById('noImageArea');
        if (displayImage) displayImage.src = uploadedImages[0].src;
        if (imageDisplayArea) imageDisplayArea.classList.remove('hidden');
        if (noImageArea) noImageArea.classList.add('hidden');
    }
}

// ---------------------------------------------------------------------------
// Navigate to size selection (save state first)
// ---------------------------------------------------------------------------
function goToSize(sizeUrl) {
    saveToSessionStorage();
    window.location.href = sizeUrl;
}

// ---------------------------------------------------------------------------
// Navigate to clean selection (save state first)
// ---------------------------------------------------------------------------
function goToClean(cleanUrl) {
    saveToSessionStorage();
    window.location.href = cleanUrl;
}

// ---------------------------------------------------------------------------
// Form validation
// ---------------------------------------------------------------------------
function validateForm() {
    saveToSessionStorage();
    let isValid = true;
    let rentalFlag = false;

    // Product name
    const productName = document.getElementById('name')?.value.trim() || '';
    setError('productNameError', !productName);
    if (!productName) isValid = false;

    // Rental / Purchase selection
    const rental   = document.getElementById('rental')?.checked || false;
    const purchase  = document.getElementById('purchase')?.checked || false;
    setError('rentalPurchaseError', !rental && !purchase);
    if (!rental && !purchase) isValid = false;

    // Rental price & period
    if (rental) {
        rentalFlag = true;
        const rentalPrice = document.getElementById('rentalPrice')?.value || '';
        setError('rentalPriceError', !rentalPrice);
        if (!rentalPrice) isValid = false;

        const rentalPeriod = document.getElementById('rentalPeriod')?.value || '';
        setError('rentalPeriodError', !rentalPeriod);
        if (!rentalPeriod) isValid = false;
    }

    // Purchase price
    if (purchase) {
        const purchasePrice = document.getElementById('purchasePrice')?.value || '';
        setError('purchasePriceError', !purchasePrice);
        if (!purchasePrice) isValid = false;
    }

    // Color
    const color = document.getElementById('color')?.value.trim() || '';
    setError('colorError', !color);
    if (!color) isValid = false;

    // Category 1
    const category1 = document.getElementById('category1')?.value || '';
    setError('category1Error', !category1);
    if (!category1) isValid = false;

    // Category 2
    const category2 = document.getElementById('category2')?.value || '';
    setError('category2Error', !category2);
    if (!category2) isValid = false;

    // Brand
    const brand = document.getElementById('brand')?.value || '';
    setError('brandError', !brand);
    if (!brand) isValid = false;

    // Size
    const sizeDisplay = document.getElementById('sizeDisplay')?.innerText.trim() || '';
    setError('sizeError', sizeDisplay === '未選択');
    if (sizeDisplay === '未選択') isValid = false;

    // Washing display
    const washingDisplay = document.getElementById('washingDisplay')?.innerText.trim() || '';
    setError('washingError', washingDisplay === '未選択');
    if (washingDisplay === '未選択') isValid = false;

    // Return location (required only when rental is selected)
    if (rentalFlag) {
        const returnEl = document.querySelector('input[name="returnLocation"]') || document.getElementById('returnLocation');
        const returnLocation = returnEl ? returnEl.value.trim() : '';
        setError('returnLocationError', !returnLocation);
        if (!returnLocation) isValid = false;
    }

    return isValid;
}

/** Toggle visibility of an error message element. */
function setError(elementId, show) {
    const el = document.getElementById(elementId);
    if (!el) return;
    if (show) {
        el.classList.remove('hidden');
    } else {
        el.classList.add('hidden');
    }
}

// ---------------------------------------------------------------------------
// Convert base64 data URL to File object
// ---------------------------------------------------------------------------
function base64ToFile(base64Data, filename) {
    const arr  = base64Data.split(',');
    const mime = arr[0].match(/:(.*?);/)[1];
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while (n--) u8arr[n] = bstr.charCodeAt(n);
    return new File([u8arr], filename, { type: mime });
}

// ---------------------------------------------------------------------------
// Build FormData with images + product JSON
// ---------------------------------------------------------------------------
function buildFormData() {
    const uploadedImages = JSON.parse(sessionStorage.getItem('uploadedImages') || '[]');
    const formData = new FormData();

    uploadedImages.forEach((imageData, index) => {
        try {
            const file = base64ToFile(imageData.src, `product_image_${index}.png`);
            formData.append('images', file);
        } catch (err) {
            console.error(`画像${index}の形式変換失敗:`, err);
        }
    });

    const productData = {
        name:          sessionStorage.getItem('name') || null,
        rental:        sessionStorage.getItem('rental') === 'true',
        purchase:      sessionStorage.getItem('purchase') === 'true',
        rentalPrice:   sessionStorage.getItem('rentalPrice') || null,
        rentalPeriod:  sessionStorage.getItem('rentalPeriod') || null,
        purchasePrice: sessionStorage.getItem('purchasePrice') || null,
        smoking:       sessionStorage.getItem('smoking') === 'yes',
        color:         sessionStorage.getItem('color') || null,
        category1:     sessionStorage.getItem('category1') || null,
        category2:     sessionStorage.getItem('category2') || null,
        brand:         sessionStorage.getItem('brand') || null,
        explanation:   sessionStorage.getItem('explanation') || null,
        returnLocation: sessionStorage.getItem('returnLocation') || null,
    };

    formData.append('productData', JSON.stringify(productData));
    return formData;
}

// ---------------------------------------------------------------------------
// Submit form (publish)
// ---------------------------------------------------------------------------
function submitForm() {
    if (!validateForm()) return;

    const formData = buildFormData();

    fetch('/seller/format/save-product', { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert('出品しました。');
                sessionStorage.clear();
                window.location.href = '/seller/seller';
            } else {
                alert('失敗: ' + data.message);
            }
        })
        .catch(err => {
            console.error('submitForm error:', err);
            alert('送信に失敗しました。再度お試しください。');
        });
}

// ---------------------------------------------------------------------------
// Submit updated product
// ---------------------------------------------------------------------------
function submitUpdateForm() {
    if (!validateForm()) return;

    const formData = buildFormData();

    fetch('/seller/format/update-product', { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert('更新しました。');
                sessionStorage.clear();
                window.location.href = '/seller/seller';
            } else {
                alert('失敗: ' + data.message);
            }
        })
        .catch(err => {
            console.error('submitUpdateForm error:', err);
            alert('送信に失敗しました。再度お試しください。');
        });
}

// ---------------------------------------------------------------------------
// Save as draft
// ---------------------------------------------------------------------------
function saveDraft() {
    saveToSessionStorage();

    const formData = buildFormData();

    fetch('/seller/format/save-product-draft', { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert('下書きに保存しました。');
                sessionStorage.clear();
                window.location.href = '/seller/seller/draft';
            } else {
                alert('失敗: ' + data.message);
            }
        })
        .catch(err => {
            console.error('saveDraft error:', err);
            alert('送信に失敗しました。再度お試しください。');
        });
}

// ---------------------------------------------------------------------------
// Navigation helpers
// ---------------------------------------------------------------------------
function backToSeller(url) {
    window.location.href = url;
}

function editProduct(productId) {
    window.location.href = `/seller/update/${productId}`;
}

// ---------------------------------------------------------------------------
// Delete product
// ---------------------------------------------------------------------------
function deleteProduct(productId) {
    if (!confirm('本当に削除しますか？')) return;

    fetch(`/seller/format/delete-product/${productId}`, { method: 'DELETE' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert('商品を削除しました。');
                window.location.reload();
            } else {
                alert('削除失敗: ' + data.message);
            }
        })
        .catch(err => {
            console.error('deleteProduct error:', err);
            alert('エラーが発生しました。');
        });
}
