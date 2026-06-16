/**
 * Consent Modal Manager
 * Handles the display, interaction, and persistence of the consent modal
 */

const ConsentModal = {
    STORAGE_KEY: 'termsConsentAccepted',
    STORAGE_EXPIRY_KEY: 'termsConsentExpiry',
    EXPIRY_DAYS: 365, // Consent valid for 1 year
    _isVisible: false,

    init() {
        // Check if consent is already given
        if (this.hasValidConsent()) {
            this.removeModal();
            return;
        }

        // Show modal if consent not found or expired
        this.showModal();
        this.attachEventListeners();
    },

    hasValidConsent() {
        const consentValue = localStorage.getItem(this.STORAGE_KEY);
        const expiryTime = localStorage.getItem(this.STORAGE_EXPIRY_KEY);

        if (!consentValue || consentValue !== 'true') {
            return false;
        }

        // Check if expiry time exists and is still valid
        if (expiryTime) {
            const now = new Date().getTime();
            if (now > parseInt(expiryTime)) {
                // Expiry time has passed, clear storage
                localStorage.removeItem(this.STORAGE_KEY);
                localStorage.removeItem(this.STORAGE_EXPIRY_KEY);
                return false;
            }
        }

        return true;
    },

    showModal() {
        const overlay = document.getElementById('consentOverlay');
        if (overlay) {
            overlay.style.display = 'flex';
            // Force reflow so the transition fires
            overlay.offsetHeight;
            overlay.classList.add('visible');
            overlay.classList.remove('hidden');
            // Prevent body scroll when modal is open
            document.body.style.overflow = 'hidden';
            this._isVisible = true;
        }
    },

    removeModal() {
        const overlay = document.getElementById('consentOverlay');
        if (overlay) {
            overlay.style.display = 'none';
            document.body.style.overflow = '';
            this._isVisible = false;
        }
    },

    attachEventListeners() {
        const checkbox = document.getElementById('consentCheckbox');
        const confirmBtn = document.getElementById('consentConfirmBtn');

        if (checkbox && confirmBtn) {
            // Enable/disable button based on checkbox state
            checkbox.addEventListener('change', (e) => {
                confirmBtn.disabled = !e.target.checked;
                if (e.target.checked) {
                    confirmBtn.classList.add('enabled');
                } else {
                    confirmBtn.classList.remove('enabled');
                }
            });

            // Handle confirm button click
            confirmBtn.addEventListener('click', () => {
                if (checkbox.checked) {
                    this.acceptConsent();
                }
            });
        }

        // Prevent escape key from closing modal
        document.addEventListener('keydown', (e) => {
            if (this._isVisible && e.key === 'Escape') {
                e.preventDefault();
                e.stopPropagation();
            }
        }, true);

        // Prevent closing modal by clicking overlay background
        const overlay = document.getElementById('consentOverlay');
        if (overlay) {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    e.preventDefault();
                    e.stopPropagation();
                }
            });
        }

        // Trap focus within the modal
        const modal = document.querySelector('.consent-modal');
        if (modal) {
            document.addEventListener('keydown', (e) => {
                if (!this._isVisible || e.key !== 'Tab') return;

                const focusable = modal.querySelectorAll(
                    'input, button:not([disabled]), [tabindex]:not([tabindex="-1"])'
                );
                const first = focusable[0];
                const last = focusable[focusable.length - 1];

                if (e.shiftKey) {
                    if (document.activeElement === first) {
                        e.preventDefault();
                        last.focus();
                    }
                } else {
                    if (document.activeElement === last) {
                        e.preventDefault();
                        first.focus();
                    }
                }
            });
        }
    },

    acceptConsent() {
        // Save consent to localStorage
        localStorage.setItem(this.STORAGE_KEY, 'true');

        // Set expiry time (365 days from now)
        const expiryTime = new Date().getTime() + (this.EXPIRY_DAYS * 24 * 60 * 60 * 1000);
        localStorage.setItem(this.STORAGE_EXPIRY_KEY, expiryTime.toString());

        // Hide modal with fade-out animation
        const overlay = document.getElementById('consentOverlay');
        if (overlay) {
            overlay.classList.add('hidden');
            overlay.classList.remove('visible');
            this._isVisible = false;

            // Wait for transition to finish, then fully remove
            overlay.addEventListener('transitionend', () => {
                overlay.style.display = 'none';
                document.body.style.overflow = '';
            }, { once: true });
        }
    }
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => ConsentModal.init());
} else {
    ConsentModal.init();
}
