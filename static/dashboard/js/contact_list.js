
// Add Modal
function openAddModal() {
    const modal = document.getElementById('addContactModal');
    modal.classList.remove('d-none');
    setTimeout(() => { modal.style.opacity = 1; modal.style.transform = 'translate(-50%, -50%) scale(1)'; }, 10);
}
function closeAddModal() {
    const modal = document.getElementById('addContactModal');
    modal.style.opacity = 0;
    modal.style.transform = 'translate(-50%, -50%) scale(0.9)';
    setTimeout(() => { modal.classList.add('d-none'); }, 300);
}

// Edit Modal
function openEditModal(id) {
    const row = document.querySelector(`#contacts-table-body tr[data-id='${id}']`);
    if (!row) return;

    document.getElementById('edit-id').value = id;
    document.getElementById('edit-name').value = row.dataset.name;
    document.getElementById('edit-phone').value = row.dataset.phone;

    const modal = document.getElementById('editContactModal');
    modal.classList.remove('d-none');
    setTimeout(() => { modal.style.opacity = 1; modal.style.transform = 'translate(-50%, -50%) scale(1)'; }, 10);
}
function closeEditModal() {
    const modal = document.getElementById('editContactModal');
    modal.style.opacity = 0;
    modal.style.transform = 'translate(-50%, -50%) scale(0.9)';
    setTimeout(() => { modal.classList.add('d-none'); }, 300);
}

// Delete Modal
function openDeleteModal(id) {
    document.getElementById('delete-id').value = id;
    const modal = document.getElementById('deleteContactModal');
    modal.classList.remove('d-none');
    setTimeout(() => { modal.style.opacity = 1; modal.style.transform = 'translate(-50%, -50%) scale(1)'; }, 10);
}
function closeDeleteModal() {
    const modal = document.getElementById('deleteContactModal');
    modal.style.opacity = 0;
    modal.style.transform = 'translate(-50%, -50%) scale(0.9)';
    setTimeout(() => { modal.classList.add('d-none'); }, 300);
}

// Auto prepend country code for Add & Edit
document.addEventListener('DOMContentLoaded', () => {

    // Add form phone field (optional)
    const addPhone = document.querySelector(
        '#id_phone_number, #add-phone, #add_phone'
    );

    if (addPhone) {
        addPhone.addEventListener('focus', () => {
            if (!addPhone.value.startsWith('256')) {
                addPhone.value = '256';
            }
        });
    }

    // Edit form phone field (SAFE)
    const editPhone = document.getElementById('edit-phone');
    if (editPhone) {
        editPhone.addEventListener('focus', () => {
            if (!editPhone.value.startsWith('256')) {
                editPhone.value = '256';
            }
        });
    }
});