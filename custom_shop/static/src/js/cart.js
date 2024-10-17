/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.websiteSaleCart = publicWidget.Widget.extend({
    selector: '.oe_website_sale .oe_cart',
    events: {
        'click .js_delete_product': '_onClickDeleteProduct',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onClickDeleteProduct: function (ev) {
        ev.preventDefault();
        const originCartDataRaw = localStorage.getItem('odoo-cart') || '[]';
        const originCartData = JSON.parse(originCartDataRaw) || [];
        const productEl = ev.currentTarget.closest('.o_cart_product');
        const productId = productEl.querySelector('.js_quantity').getAttribute('data-product-id');
        const newData = originCartData.filter(item => item.product_id != productId);
        localStorage.setItem('odoo-cart',JSON.stringify(newData));
        $(ev.currentTarget).closest('.o_cart_product').find('.js_quantity').val(0).trigger('change');
    },
});
