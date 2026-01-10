package com.example.fitnesscoachai

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.example.fitnesscoachai.ui.auth.AuthActivity
import com.example.fitnesscoachai.ui.camera.CameraActivity
import com.example.fitnesscoachai.ui.home.HomeFragment
import com.example.fitnesscoachai.ui.profile.ProfileFragment

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val isLoggedIn = getSharedPreferences("auth", MODE_PRIVATE)
            .getBoolean("isLoggedIn", false)

        if (!isLoggedIn) {
            startActivity(Intent(this, AuthActivity::class.java))
            finish()
            return
        }
        
        setContentView(R.layout.activity_main)

        openFragment(HomeFragment())

        val bottomNavigation = findViewById<BottomNavigationView>(R.id.bottomNavigation)
        bottomNavigation.setOnItemSelectedListener {
            when (it.itemId) {
                R.id.nav_home -> openFragment(HomeFragment())
                R.id.nav_camera -> {
                    startActivity(Intent(this, CameraActivity::class.java))
                }
                R.id.nav_profile -> openFragment(ProfileFragment())
            }
            true
        }
    }

    private fun openFragment(fragment: Fragment) {
        supportFragmentManager.beginTransaction()
            .replace(R.id.container, fragment)
            .commit()
    }
}